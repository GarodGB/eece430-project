"""Receipt intake must be atomic, validated, pharmacy-scoped, and idempotent."""
from datetime import date, timedelta
from django.test import TestCase
from django.db.models import Sum
from rest_framework.test import APIClient
from accounts.models import Pharmacy, User
from inventory.models import Medicine, Stock
from prediction.models import PurchaseOrder, Supplier

class ReceiveDeliveryTests(TestCase):
    def setUp(self):
        self.pharmacy = Pharmacy.objects.create(name='Intake Pharmacy', address='Beirut', phone='01000111')
        self.other = Pharmacy.objects.create(name='Outside Pharmacy', address='Saida', phone='01000222')
        self.owner = User.objects.create_user(username='receipt_owner', role='owner', pharmacy=self.pharmacy, password='TestPassword123!')
        self.pharmacist = User.objects.create_user(username='receipt_pharm', role='pharmacist', pharmacy=self.pharmacy, password='TestPassword123!')
        self.outside_owner = User.objects.create_user(username='outside_owner', role='owner', pharmacy=self.other, password='TestPassword123!')
        self.medicine = Medicine.objects.create(name='Intake Medicine', barcode='8898007', price='10.00', cost='4.00')
        self.supplier = Supplier.objects.create(name='Intake Supplier', phone='11223344')
        self.stock = Stock.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, quantity=3, reorder_level=10, expiry_date=date.today()+timedelta(days=90))
        self.order = PurchaseOrder.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, supplier=self.supplier, quantity=8, status='sent')
        self.client = APIClient()
        self.url = f'/api/reorder/orders/{self.order.pk}/'
        self.expiry = (date.today()+timedelta(days=180)).isoformat()

    def payload(self, quantity=8, expiry=None):
        return {'status': 'received', 'received_quantity': quantity, 'expiry_date': expiry or self.expiry}

    def test_received_creates_one_batch_and_records_receipt(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(self.url, self.payload(), format='json')
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'received')
        self.assertEqual(self.order.received_quantity, 8)
        self.assertEqual(str(self.order.received_expiry_date), self.expiry)
        self.assertIsNotNone(self.order.received_at)
        self.assertIsNotNone(self.order.received_stock_id)
        self.assertEqual(self.order.received_stock.quantity, 8)
        self.assertEqual(self.order.received_stock.reorder_level, 10)
        self.assertEqual(Stock.objects.filter(pharmacy=self.pharmacy, medicine=self.medicine).aggregate(total=Sum('quantity'))['total'], 11)
        self.assertEqual(response.data['received_stock_id'], self.order.received_stock_id)

    def test_retry_does_not_double_count(self):
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.patch(self.url, self.payload(), format='json').status_code, 200)
        again=self.client.patch(self.url, self.payload(), format='json')
        self.assertEqual(again.status_code, 200)
        self.assertEqual(Stock.objects.filter(pharmacy=self.pharmacy, medicine=self.medicine).count(), 2)
        self.assertEqual(Stock.objects.filter(pharmacy=self.pharmacy, medicine=self.medicine).aggregate(total=Sum('quantity'))['total'], 11)
        self.assertEqual(self.client.patch(self.url, self.payload(quantity=9), format='json').status_code, 409)

    def test_invalid_receipt_fields_do_not_change_stock_or_order(self):
        self.client.force_authenticate(user=self.owner)
        cases=[{'status':'received'}, self.payload(quantity=0), self.payload(expiry=(date.today()-timedelta(days=1)).isoformat())]
        for case in cases:
            with self.subTest(payload=case):
                self.assertEqual(self.client.patch(self.url, case, format='json').status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'sent')
        self.assertEqual(Stock.objects.filter(pharmacy=self.pharmacy, medicine=self.medicine).count(), 1)

    def test_pending_order_must_be_sent_first(self):
        self.order.status='pending'
        self.order.save(update_fields=['status'])
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.patch(self.url, self.payload(), format='json').status_code, 409)
        self.assertEqual(Stock.objects.filter(pharmacy=self.pharmacy, medicine=self.medicine).count(), 1)

    def test_pharmacist_and_other_owner_cannot_receive(self):
        for user, expected in [(self.pharmacist,403),(self.outside_owner,404)]:
            with self.subTest(user=user.username):
                self.client.force_authenticate(user=user)
                self.assertEqual(self.client.patch(self.url, self.payload(), format='json').status_code, expected)
        self.assertEqual(Stock.objects.filter(pharmacy=self.pharmacy, medicine=self.medicine).count(), 1)

    def test_legacy_received_order_not_credited_again(self):
        self.order.status='received'
        self.order.save(update_fields=['status'])
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.patch(self.url, self.payload(), format='json').status_code, 200)
        self.assertEqual(Stock.objects.filter(pharmacy=self.pharmacy, medicine=self.medicine).count(), 1)
