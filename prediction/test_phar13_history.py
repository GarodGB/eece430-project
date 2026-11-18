"""PHAR-13: owner-only purchase order history/status transitions."""
from datetime import date
from django.test import TestCase
from django.db.models import Sum
from rest_framework.test import APIClient
from accounts.models import Pharmacy, User
from inventory.models import Medicine, Stock
from prediction.models import PurchaseOrder, Supplier


class PurchaseOrderStatusTests(TestCase):
    def setUp(self):
        self.pharmacy = Pharmacy.objects.create(name='History Beirut', address='Beirut', phone='11223344')
        self.other = Pharmacy.objects.create(name='History Other', address='Baabda', phone='22334455')
        self.owner = User.objects.create_user(username='history_owner', role='owner', pharmacy=self.pharmacy, password='TestPassword123!')
        self.other_owner = User.objects.create_user(username='history_other', role='owner', pharmacy=self.other, password='TestPassword123!')
        self.pharmacist = User.objects.create_user(username='history_pharmacist', role='pharmacist', pharmacy=self.pharmacy, password='TestPassword123!')
        self.medicine = Medicine.objects.create(name='History Medicine', barcode='923003904', price='5.00', cost='2.00')
        self.supplier = Supplier.objects.create(name='History Supplier', phone='12345678')
        self.stock = Stock.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, quantity=2, reorder_level=10, expiry_date=date(2028, 1, 1))
        self.order = PurchaseOrder.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, supplier=self.supplier, quantity=8, status='pending')
        self.client = APIClient()
        self.url = f'/api/reorder/orders/{self.order.id}/'

    def test_anonymous_cannot_update(self):
        response = self.client.patch(self.url, {'status': 'sent'}, format='json')
        self.assertEqual(response.status_code, 401)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'pending')

    def test_pharmacist_cannot_update(self):
        self.client.force_authenticate(user=self.pharmacist)
        self.assertEqual(self.client.patch(self.url, {'status': 'sent'}, format='json').status_code, 403)

    def test_other_owner_cannot_access_order(self):
        self.client.force_authenticate(user=self.other_owner)
        self.assertEqual(self.client.patch(self.url, {'status': 'sent'}, format='json').status_code, 404)
        self.assertEqual(PurchaseOrder.objects.get(id=self.order.id).status, 'pending')

    def test_pending_to_sent_to_received_adds_stock_batch(self):
        self.client.force_authenticate(user=self.owner)
        first = self.client.patch(self.url, {'status': 'sent'}, format='json')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data['status'], 'sent')
        second = self.client.patch(self.url, {'status': 'received', 'received_quantity': 8, 'expiry_date': '2028-06-30'}, format='json')
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data['status'], 'received')
        self.assertEqual(Stock.objects.get(id=self.stock.id).quantity, 2)
        self.assertEqual(Stock.objects.filter(pharmacy=self.pharmacy, medicine=self.medicine).aggregate(total=Sum('quantity'))['total'], 10)
        self.assertEqual(PurchaseOrder.objects.get(id=self.order.id).received_quantity, 8)

    def test_cannot_skip_sent(self):
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.patch(self.url, {'status': 'received'}, format='json').status_code, 409)
        self.assertEqual(PurchaseOrder.objects.get(id=self.order.id).status, 'pending')

    def test_cannot_rewind_received(self):
        self.order.status = 'received'
        self.order.save(update_fields=['status'])
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.patch(self.url, {'status': 'sent'}, format='json').status_code, 409)
        self.assertEqual(PurchaseOrder.objects.get(id=self.order.id).status, 'received')

    def test_invalid_status_rejected(self):
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.patch(self.url, {'status': 'cancelled'}, format='json').status_code, 400)
        self.assertEqual(PurchaseOrder.objects.get(id=self.order.id).status, 'pending')

    def test_repeated_update_is_idempotent(self):
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.patch(self.url, {'status': 'sent'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(self.url, {'status': 'sent'}, format='json').status_code, 200)
        self.assertEqual(PurchaseOrder.objects.filter(id=self.order.id).count(), 1)

    def test_history_includes_older_received_orders(self):
        old_order = PurchaseOrder.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, supplier=self.supplier, quantity=5, status='received')
        other_order = PurchaseOrder.objects.create(pharmacy=self.other, medicine=self.medicine, supplier=self.supplier, quantity=7, status='pending')
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/reorder/orders/')
        self.assertEqual(response.status_code, 200)
        returned_ids = {row['id'] for row in response.data}
        self.assertIn(old_order.id, returned_ids)
        self.assertIn(self.order.id, returned_ids)
        self.assertNotIn(other_order.id, returned_ids)
