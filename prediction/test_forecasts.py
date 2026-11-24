from datetime import date, datetime, timedelta, timezone as utc
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Pharmacy, User
from inventory.models import Medicine, MedicineReservation, Stock
from prediction.models import DailySales
from sales.models import Sale, SaleItem


class StockForecastTests(TestCase):
    url = '/api/prediction/forecasts/'
    # It is already July 1 in Beirut while it is still June 30 in UTC.
    now = datetime(2026, 6, 30, 22, tzinfo=utc.utc)
    today = date(2026, 7, 1)

    @classmethod
    def setUpTestData(cls):
        cls.pharmacy = Pharmacy.objects.create(name='Demo Pharmacy Beirut')
        cls.other = Pharmacy.objects.create(name='Other pharmacy')
        cls.staff = User.objects.create(username='staff', role='pharmacist', pharmacy=cls.pharmacy)
        cls.med = Medicine.objects.create(
            name='Demo medicine', generic_name='Generic', barcode='00123', price=5, cost=2,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.staff)
        clock = patch('django.utils.timezone.now', return_value=self.now)
        clock.start()
        self.addCleanup(clock.stop)

    def stock(self, quantity, expires_in=10, pharmacy=None, medicine=None):
        return Stock.objects.create(
            pharmacy=pharmacy or self.pharmacy, medicine=medicine or self.med,
            quantity=quantity, expiry_date=self.today + timedelta(days=expires_in),
        )

    def sales(self, quantity, days_ago, pharmacy=None):
        return DailySales.objects.create(
            pharmacy=pharmacy or self.pharmacy, medicine=self.med,
            date=self.today - timedelta(days=days_ago), quantity_sold=quantity,
        )

    def response(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_uses_exactly_thirty_completed_beirut_days_and_rounds_up(self):
        self.stock(11)
        self.sales(1000, 31)
        self.sales(30, 30)
        self.sales(30, 1)
        self.sales(1000, 0)
        self.sales(1000, -1)
        result = self.response()
        self.assertEqual(result['as_of_date'], '2026-07-01')
        self.assertEqual(result['lookback_days'], 30)
        self.assertEqual(result['forecasts'], [{
            'medicine_id': self.med.pk, 'medicine_name': self.med.name,
            'generic_name': 'Generic', 'barcode': '00123', 'available_quantity': 11,
            'total_units_sold': 60, 'average_daily_sales': 2.0, 'days_remaining': 6,
            'predicted_run_out_date': '2026-07-07', 'status': 'estimated',
        }])

    def test_batches_expiry_and_active_and_released_reservations(self):
        self.stock(6, expires_in=0)
        self.stock(8)
        self.stock(90, expires_in=-1)
        hold = MedicineReservation.objects.create(
            pharmacy=self.pharmacy, medicine=self.med, quantity=3, customer_name='Customer',
        )
        MedicineReservation.objects.create(
            pharmacy=self.pharmacy, medicine=self.med, quantity=2, customer_name='Another customer',
        )
        MedicineReservation.objects.create(
            pharmacy=self.pharmacy, medicine=self.med, quantity=99, customer_name='Released',
            status=MedicineReservation.RELEASED,
        )
        self.sales(60, 1)
        forecast, = self.response()['forecasts']
        self.assertEqual(forecast['available_quantity'], 9)
        self.assertEqual(forecast['days_remaining'], 5)

        response = self.client.post(f'/api/reservations/{hold.pk}/release/')
        self.assertEqual(response.status_code, 200)
        forecast, = self.response()['forecasts']
        self.assertEqual(forecast['available_quantity'], 12)
        self.assertEqual(forecast['days_remaining'], 6)

    def test_zero_sellable_stock_takes_precedence_over_missing_sales(self):
        self.stock(2)
        MedicineReservation.objects.create(
            pharmacy=self.pharmacy, medicine=self.med, quantity=5, customer_name='Customer',
        )
        forecast, = self.response()['forecasts']
        self.assertEqual(forecast['status'], 'out_of_stock')
        self.assertEqual(forecast['available_quantity'], 0)
        self.assertEqual(forecast['days_remaining'], 0)
        self.assertEqual(forecast['predicted_run_out_date'], '2026-07-01')

    def test_expired_only_stock_is_out_of_stock_even_with_sales(self):
        self.stock(5, expires_in=-1)
        self.sales(30, 1)
        forecast, = self.response()['forecasts']
        self.assertEqual(forecast['status'], 'out_of_stock')
        self.assertEqual(forecast['total_units_sold'], 30)

    def test_sparse_sales_use_the_unrounded_rate(self):
        self.stock(1)
        self.sales(1, 1)
        forecast, = self.response()['forecasts']
        self.assertEqual(forecast['days_remaining'], 30)
        self.assertEqual(forecast['predicted_run_out_date'], '2026-07-31')

    def test_large_estimate_preserves_days_when_date_is_out_of_range(self):
        self.stock(100000)
        self.sales(1, 1)
        forecast, = self.response()['forecasts']
        self.assertEqual(forecast['days_remaining'], 3000000)
        self.assertIsNone(forecast['predicted_run_out_date'])

    def test_isolates_inventory_reservations_and_sales_by_pharmacy(self):
        self.stock(7)
        self.stock(50, pharmacy=self.other)
        other_med = Medicine.objects.create(name='Other medicine', barcode='456', price=3, cost=1)
        self.stock(100, pharmacy=self.other, medicine=other_med)
        MedicineReservation.objects.create(
            pharmacy=self.other, medicine=self.med, quantity=6, customer_name='Other pharmacy customer',
        )
        self.sales(90, 1, pharmacy=self.other)
        self.sales(99, 31)
        forecast, = self.response()['forecasts']
        self.assertEqual(forecast['medicine_id'], self.med.pk)
        self.assertEqual(forecast['available_quantity'], 7)
        self.assertEqual(forecast['total_units_sold'], 0)
        self.assertEqual(forecast['average_daily_sales'], 0)
        self.assertEqual(forecast['status'], 'no_recent_sales')
        self.assertIsNone(forecast['days_remaining'])
        self.assertIsNone(forecast['predicted_run_out_date'])

    def test_checkout_records_sales_on_beirut_date_and_counts_them_next_day(self):
        stock = self.stock(6, expires_in=0)
        self.stock(5)
        response = self.client.post('/api/sales/', {
            'items': [{'barcode': self.med.barcode, 'quantity': 3}],
        }, format='json')
        self.assertEqual(response.status_code, 201)
        daily = DailySales.objects.get(pharmacy=self.pharmacy, medicine=self.med)
        self.assertEqual(daily.date, self.today)
        self.assertEqual(daily.quantity_sold, 3)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity, 3)
        self.assertEqual(self.response()['forecasts'][0]['status'], 'no_recent_sales')
        with patch('django.utils.timezone.now', return_value=self.now + timedelta(days=1)):
            forecast, = self.response()['forecasts']
        self.assertEqual(forecast['available_quantity'], 5)
        self.assertEqual(forecast['total_units_sold'], 3)
        self.assertEqual(forecast['days_remaining'], 50)

    def test_read_only_and_requires_pharmacy_membership(self):
        self.assertEqual(self.response()['forecasts'], [])
        self.assertEqual(self.client.post(self.url).status_code, 405)
        unattached = User.objects.create(username='unattached', role='pharmacist')
        self.client.force_authenticate(unattached)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_demo_seed_is_opt_in_and_preserves_existing_records(self):
        self.stock(20)
        seeded_med = Medicine.objects.create(name='Demo seedable', barcode='456', price=5, cost=2)
        sold_med = Medicine.objects.create(name='Demo sold', barcode='789', price=5, cost=2)
        self.stock(20, medicine=seeded_med)
        self.stock(20, medicine=sold_med)
        existing = DailySales.objects.create(
            pharmacy=self.pharmacy, medicine=seeded_med,
            date=self.today - timedelta(days=30), quantity_sold=99,
        )
        sale = Sale.objects.create(pharmacy=self.pharmacy)
        SaleItem.objects.create(sale=sale, medicine=sold_med, quantity=1, unit_price=5)
        args = ['--pharmacy-id', str(self.pharmacy.pk), '--as-of', self.today.isoformat()]
        with self.assertRaises(CommandError):
            call_command('seed_forecast_demo', *args, stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command('seed_forecast_demo', '--demo-only', '--pharmacy-id', str(self.other.pk))

        call_command('seed_forecast_demo', *args, '--demo-only', stdout=StringIO())
        history = list(DailySales.objects.order_by('id').values())
        self.assertGreater(len(history), 1)
        self.assertTrue(all(row['medicine_id'] == seeded_med.pk for row in history))
        self.assertTrue(all(self.today - timedelta(days=30) <= row['date'] < self.today for row in history))
        call_command('seed_forecast_demo', *args, '--demo-only', stdout=StringIO())
        self.assertEqual(list(DailySales.objects.order_by('id').values()), history)
        existing.refresh_from_db()
        self.assertEqual(existing.quantity_sold, 99)
        self.assertEqual(list(Stock.objects.values_list('quantity', flat=True)), [20, 20, 20])
        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(SaleItem.objects.count(), 1)
