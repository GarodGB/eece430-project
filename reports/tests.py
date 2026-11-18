from datetime import datetime, time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Pharmacy, User
from inventory.models import Medicine
from sales.models import Sale, SaleItem

URL = '/api/reports/weekly/'


def local_time(day, hour, minute=0):
    """A time on a given day, in Lebanon time."""
    return timezone.make_aware(datetime.combine(day, time(hour, minute)), timezone.get_current_timezone())


class WeeklyReportTests(TestCase):
    """PHAR-14: weekly sales and profit, owner only."""

    def setUp(self):
        self.pharmacy = Pharmacy.objects.create(name="Report Pharmacy", address="Beirut", phone="11111111")
        self.other = Pharmacy.objects.create(name="Other Pharmacy", address="Baabda", phone="22222222")
        self.owner = User.objects.create_user(username="reportowner", password="TestPassword123!",
                                              role="owner", pharmacy=self.pharmacy)
        self.pharmacist = User.objects.create_user(username="reportpharmacist", password="TestPassword123!",
                                                   role="pharmacist", pharmacy=self.pharmacy)
        self.panadol = Medicine.objects.create(name="Panadol", barcode="8200001", price="4.00", cost="2.00")
        self.brufen = Medicine.objects.create(name="Brufen", barcode="8200002", price="5.00", cost="3.00")
        self.panadol.refresh_from_db()  # prices as Decimal, like in real use
        self.brufen.refresh_from_db()

        today = timezone.localdate()
        self.this_monday = today - timedelta(days=today.weekday())
        self.last_monday = self.this_monday - timedelta(weeks=1)

        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

    def make_sale(self, when, items, discount='0', pharmacy=None, unit_cost=True):
        """items: list of (medicine, quantity). Saves the sale the same way the Point of Sale does."""
        subtotal = sum((m.price * q for m, q in items), Decimal('0'))
        total = (subtotal * (100 - Decimal(discount)) / 100).quantize(Decimal('0.01'))
        sale = Sale.objects.create(pharmacy=pharmacy or self.pharmacy, sold_by=self.owner,
                                   subtotal=subtotal, discount_percent=discount, total=total)
        for medicine, quantity in items:
            SaleItem.objects.create(sale=sale, medicine=medicine, quantity=quantity, unit_price=medicine.price,
                                    unit_cost=medicine.cost if unit_cost else None)
        Sale.objects.filter(pk=sale.pk).update(created_at=when)  # created_at is set automatically
        return sale

    def get(self, weeks=None):
        return self.client.get(URL, {} if weeks is None else {'weeks': weeks})

    def week(self, data, monday):
        return next(w for w in data['results'] if w['week_start'] == monday.isoformat())

    # ---------- Who can see it ----------

    def test_owner_can_see_report(self):
        self.assertEqual(self.get().status_code, 200)

    def test_pharmacist_is_refused(self):
        self.client.force_authenticate(user=self.pharmacist)
        response = self.get()
        self.assertEqual(response.status_code, 403)
        self.assertIn("Only the pharmacy owner", str(response.data))

    def test_system_admin_is_refused(self):
        admin = User.objects.create_superuser(username="reportadmin", password="TestPassword123!", role="admin")
        self.client.force_authenticate(user=admin)
        self.assertEqual(self.get().status_code, 403)

    def test_not_logged_in_is_refused(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.get().status_code, 401)

    def test_only_get_is_allowed(self):
        self.assertEqual(self.client.post(URL, {}).status_code, 405)

    # ---------- The weeks parameter ----------

    def test_default_is_8_weeks_newest_first(self):
        data = self.get().data
        self.assertEqual(data['weeks'], 8)
        self.assertEqual(len(data['results']), 8)
        self.assertEqual(data['results'][0]['week_start'], self.this_monday.isoformat())
        self.assertTrue(data['results'][0]['is_current'])
        self.assertFalse(any(w['is_current'] for w in data['results'][1:]))
        starts = [w['week_start'] for w in data['results']]
        self.assertEqual(starts, sorted(starts, reverse=True))

    def test_weeks_run_monday_to_sunday(self):
        for w in self.get().data['results']:
            start = datetime.fromisoformat(w['week_start']).date()
            end = datetime.fromisoformat(w['week_end']).date()
            self.assertEqual(start.weekday(), 0)  # Monday
            self.assertEqual((end - start).days, 6)  # Sunday

    def test_smallest_and_largest_weeks(self):
        self.assertEqual(len(self.get(1).data['results']), 1)
        self.assertEqual(len(self.get(52).data['results']), 52)

    def test_bad_weeks_values_are_refused(self):
        for value in ['0', '53', '-1', 'abc', '1.5', '', '1e2']:
            response = self.get(value)
            self.assertEqual(response.status_code, 400, value)
            self.assertIn('1 to 52', str(response.data))

    # ---------- The numbers ----------

    def test_empty_pharmacy_shows_zeros(self):
        data = self.get(4).data
        for w in data['results']:
            self.assertEqual((w['sales_count'], w['revenue'], w['cost'], w['profit']), (0, '0.00', '0.00', '0.00'))
            self.assertIsNone(w['margin_percent'])
        self.assertEqual(data['totals']['revenue'], '0.00')
        self.assertIsNone(data['totals']['margin_percent'])

    def test_revenue_cost_and_profit(self):
        # 2 x Panadol (4.00, cost 2.00) + 1 x Brufen (5.00, cost 3.00): revenue 13.00, cost 7.00, profit 6.00
        self.make_sale(local_time(self.this_monday, 10), [(self.panadol, 2), (self.brufen, 1)])
        w = self.week(self.get().data, self.this_monday)
        self.assertEqual(w['sales_count'], 1)
        self.assertEqual(w['revenue'], '13.00')
        self.assertEqual(w['cost'], '7.00')
        self.assertEqual(w['profit'], '6.00')
        self.assertEqual(w['margin_percent'], '46.15')

    def test_revenue_is_after_discount(self):
        # Same sale with 10% discount: customer pays 11.70, cost 7.00, profit 4.70
        self.make_sale(local_time(self.this_monday, 10), [(self.panadol, 2), (self.brufen, 1)], discount='10')
        w = self.week(self.get().data, self.this_monday)
        self.assertEqual(w['revenue'], '11.70')
        self.assertEqual(w['profit'], '4.70')

    def test_cost_uses_price_on_the_day_of_the_sale(self):
        self.make_sale(local_time(self.this_monday, 10), [(self.panadol, 1)])
        Medicine.objects.filter(pk=self.panadol.pk).update(cost='3.50')  # cost changes later
        w = self.week(self.get().data, self.this_monday)
        self.assertEqual(w['cost'], '2.00')
        self.assertFalse(w['cost_estimated'])

    def test_old_sale_without_cost_uses_current_cost_and_is_marked(self):
        self.make_sale(local_time(self.last_monday, 10), [(self.panadol, 3)], unit_cost=False)
        data = self.get().data
        w = self.week(data, self.last_monday)
        self.assertEqual(w['cost'], '6.00')
        self.assertTrue(w['cost_estimated'])
        self.assertTrue(data['totals']['cost_estimated'])
        self.assertFalse(self.week(data, self.this_monday)['cost_estimated'])

    def test_sales_go_in_the_right_week(self):
        self.make_sale(local_time(self.this_monday, 9), [(self.panadol, 1)])
        self.make_sale(local_time(self.last_monday + timedelta(days=3), 9), [(self.brufen, 1)])
        self.make_sale(local_time(self.last_monday + timedelta(days=4), 9), [(self.brufen, 1)])
        data = self.get().data
        self.assertEqual(self.week(data, self.this_monday)['sales_count'], 1)
        self.assertEqual(self.week(data, self.last_monday)['sales_count'], 2)
        self.assertEqual(self.week(data, self.last_monday)['revenue'], '10.00')

    def test_week_boundary_uses_lebanon_time(self):
        # Sunday 23:30 in Beirut is still last week; Monday 00:30 in Beirut is this week,
        # even though in UTC both are on Sunday.
        self.make_sale(local_time(self.this_monday - timedelta(days=1), 23, 30), [(self.panadol, 1)])
        self.make_sale(local_time(self.this_monday, 0, 30), [(self.brufen, 1)])
        data = self.get().data
        self.assertEqual(self.week(data, self.last_monday)['revenue'], '4.00')
        self.assertEqual(self.week(data, self.this_monday)['revenue'], '5.00')

    def test_other_pharmacies_are_not_counted(self):
        self.make_sale(local_time(self.this_monday, 10), [(self.panadol, 5)], pharmacy=self.other)
        self.assertEqual(self.week(self.get().data, self.this_monday)['sales_count'], 0)

    def test_sales_before_the_period_are_not_counted(self):
        self.make_sale(local_time(self.this_monday - timedelta(weeks=4), 10), [(self.panadol, 1)])
        data = self.get(4).data
        self.assertEqual(data['totals']['sales_count'], 0)
        self.assertEqual(self.get(5).data['totals']['sales_count'], 1)

    def test_totals_add_up_all_weeks(self):
        self.make_sale(local_time(self.this_monday, 10), [(self.panadol, 2), (self.brufen, 1)])  # 13.00 / 7.00
        self.make_sale(local_time(self.last_monday, 10), [(self.brufen, 2)])  # 10.00 / 6.00
        totals = self.get().data['totals']
        self.assertEqual(totals['sales_count'], 2)
        self.assertEqual(totals['revenue'], '23.00')
        self.assertEqual(totals['cost'], '13.00')
        self.assertEqual(totals['profit'], '10.00')
        self.assertEqual(totals['margin_percent'], '43.48')

    def test_loss_shows_negative_profit(self):
        # A 100% discount: customer pays 0, cost 2.00 (can't happen in the app, but the report must not break)
        self.make_sale(local_time(self.this_monday, 10), [(self.panadol, 1)], discount='100')
        w = self.week(self.get().data, self.this_monday)
        self.assertEqual(w['profit'], '-2.00')
        self.assertIsNone(w['margin_percent'])

    def test_real_sale_from_point_of_sale_appears(self):
        """End to end: a sale made through the sales API shows up in the report."""
        from datetime import date
        from inventory.models import Stock
        Stock.objects.create(pharmacy=self.pharmacy, medicine=self.panadol, quantity=10,
                             expiry_date=date.today() + timedelta(days=200))
        self.client.force_authenticate(user=self.pharmacist)
        self.assertEqual(self.client.post('/api/sales/', {'items': [{'barcode': '8200001', 'quantity': 3}]},
                                          format='json').status_code, 201)
        self.client.force_authenticate(user=self.owner)
        w = self.get().data['results'][0]
        self.assertEqual((w['sales_count'], w['revenue'], w['cost'], w['profit']), (1, '12.00', '6.00', '6.00'))
