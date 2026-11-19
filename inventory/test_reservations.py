from datetime import date, timedelta
from uuid import uuid4
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import Pharmacy, User
from inventory.models import Medicine, MedicineReservation, Stock
from sales.models import Sale


class MedicineReservationTests(TestCase):
    def setUp(self):
        self.p1 = Pharmacy.objects.create(name='P1', address='Beirut', phone='11111111')
        self.p2 = Pharmacy.objects.create(name='P2', address='Baabda', phone='22222222')
        self.pharmacist = User.objects.create_user(
            username='reservationpharmacist', password='SafePass123!',
            role='pharmacist', pharmacy=self.p1)
        self.other = User.objects.create_user(
            username='reservationother', password='SafePass123!',
            role='pharmacist', pharmacy=self.p2)
        self.owner = User.objects.create_user(
            username='reservationowner', password='SafePass123!',
            role='owner', pharmacy=self.p1)
        self.med = Medicine.objects.create(
            name='Medicine A', barcode='55500001', price='5.00', cost='2.00')
        self.stock = Stock.objects.create(
            pharmacy=self.p1, medicine=self.med, quantity=10, reorder_level=5,
            expiry_date=date.today() + timedelta(days=100))
        self.other_stock = Stock.objects.create(
            pharmacy=self.p2, medicine=self.med, quantity=6,
            expiry_date=date.today() + timedelta(days=100))
        self.client = APIClient()
        self.client.force_authenticate(user=self.pharmacist)

    def reserve(self, quantity=3, **kwargs):
        return self.client.post('/api/reservations/', {
            'medicine_id': self.med.pk, 'quantity': quantity,
            'customer_name': 'Demo Customer', **kwargs,
        }, format='json')

    def sell(self, quantity):
        return self.client.post('/api/sales/', {
            'items': [{'barcode': self.med.barcode, 'quantity': quantity}],
        }, format='json')

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get('/api/reservations/').status_code, 401)
        self.assertEqual(self.client.post('/api/reservations/', {}).status_code, 401)

    def test_reservation_records_customer_and_pharmacist(self):
        response = self.reserve(3, customer_phone='03123456')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['customer_name'], 'Demo Customer')
        self.assertEqual(response.data['reserved_by'], self.pharmacist.username)
        self.assertEqual(response.data['customer_phone'], '03123456')
        self.assertEqual(response.data['status'], 'active')
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)

    def test_cannot_overreserve(self):
        self.assertEqual(self.reserve(7).status_code, 201)
        self.assertEqual(self.reserve(4).status_code, 400)
        self.assertEqual(MedicineReservation.objects.count(), 1)

    def test_checkout_protects_reserved_units(self):
        self.assertEqual(self.reserve(3).status_code, 201)
        response = self.sell(8)
        self.assertEqual(response.status_code, 400)
        self.assertIn('reserved', str(response.data).lower())
        self.assertEqual(Sale.objects.count(), 0)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)
        self.assertEqual(self.sell(7).status_code, 201)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 3)
        self.assertEqual(MedicineReservation.objects.get().status, 'active')
        self.assertEqual(self.sell(1).status_code, 400)

    def test_release_frees_stock_and_records_actor(self):
        r = self.reserve(10)
        self.assertEqual(self.sell(1).status_code, 400)
        released = self.client.post(f"/api/reservations/{r.data['id']}/release/")
        self.assertEqual(released.status_code, 200)
        self.assertEqual(released.data['status'], 'released')
        self.assertEqual(released.data['released_by'], self.pharmacist.username)
        self.assertEqual(self.sell(10).status_code, 201)

    def test_release_twice_is_safe(self):
        r = self.reserve(5)
        path = f"/api/reservations/{r.data['id']}/release/"
        self.assertEqual(self.client.post(path).status_code, 200)
        self.assertEqual(self.client.post(path).status_code, 200)
        self.assertEqual(MedicineReservation.objects.filter(status='released').count(), 1)

    def test_isolation_between_pharmacies(self):
        own = self.reserve(2)
        self.client.force_authenticate(user=self.other)
        self.assertEqual(list(self.client.get('/api/reservations/').data), [])
        self.assertEqual(
            self.client.post(f"/api/reservations/{own.data['id']}/release/").status_code, 404)
        self.assertEqual(self.reserve(7).status_code, 400)
        self.assertEqual(MedicineReservation.objects.get(pk=own.data['id']).status, 'active')

    def test_owner_can_reserve_and_release(self):
        self.client.force_authenticate(user=self.owner)
        r = self.reserve(1)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            self.client.post(f"/api/reservations/{r.data['id']}/release/").status_code, 200)

    def test_idempotency_key_on_retry(self):
        key = str(uuid4())
        first = self.reserve(2, request_key=key)
        second = self.reserve(2, request_key=key)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertEqual(MedicineReservation.objects.count(), 1)

    def test_stock_endpoint_reports_sellable_quantity(self):
        self.reserve(4)
        response = self.client.get('/api/stock/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['total_quantity'], 10)
        self.assertEqual(response.data[0]['reserved_quantity'], 4)
        self.assertEqual(response.data[0]['available_to_sell'], 6)

    def test_finder_ignores_fully_reserved_pharmacy_stock(self):
        self.p2.shares_stock = True
        self.p2.save()
        self.client.force_authenticate(user=self.other)
        self.assertEqual(self.reserve(6).status_code, 201)
        self.client.force_authenticate(user=self.pharmacist)
        response = self.client.get('/api/finder/?q=Medicine')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(any(row['pharmacy']['name'] == 'P2' for row in response.data))

    def test_expired_stock_is_not_reservable(self):
        self.stock.expiry_date = date.today() - timedelta(days=1)
        self.stock.save(update_fields=['expiry_date'])
        self.assertEqual(self.reserve(1).status_code, 400)

    def test_reservations_affect_low_stock_alerts_and_reordering(self):
        from prediction.models import Supplier, PurchaseOrder
        self.stock.reorder_level = 9
        self.stock.save(update_fields=['reorder_level'])
        self.assertEqual(list(self.client.get('/api/alerts/low-stock/').data), [])
        self.assertEqual(self.reserve(2).status_code, 201)
        alerts = self.client.get('/api/alerts/low-stock/')
        self.assertEqual(alerts.status_code, 200)
        self.assertEqual(len(alerts.data), 1)
        self.assertEqual(alerts.data[0]['available_quantity'], 8)
        self.client.force_authenticate(user=self.owner)
        supplier = Supplier.objects.create(name='Demo Supplier', phone='03123456')
        result = self.client.post('/api/reorder/orders/', {
            'medicine_id': self.med.pk, 'supplier_id': supplier.pk, 'quantity': 4,
        }, format='json')
        self.assertEqual(result.status_code, 201)
        self.assertEqual(PurchaseOrder.objects.count(), 1)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)
