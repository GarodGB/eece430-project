"""PHAR-13: pending reorder API tests, isolated from local demo database."""
from datetime import date
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import Pharmacy, User
from inventory.models import Medicine, Stock
from prediction.models import PurchaseOrder, Supplier


class PendingReorderTests(TestCase):
    URL = '/api/reorder/orders/'
    SUPPLIERS = '/api/reorder/suppliers/'

    def setUp(self):
        self.beirut = Pharmacy.objects.create(name='Reorder Beirut', address='Beirut', phone='11111111')
        self.other = Pharmacy.objects.create(name='Reorder Other', address='Baabda', phone='22222222')
        self.owner = User.objects.create_user(
            username='reorder_owner', password='TestPassword123!', role='owner', pharmacy=self.beirut)
        self.pharmacist = User.objects.create_user(
            username='reorder_pharmacist', password='TestPassword123!', role='pharmacist', pharmacy=self.beirut)
        self.other_owner = User.objects.create_user(
            username='reorder_other_owner', password='TestPassword123!', role='owner', pharmacy=self.other)
        self.med = Medicine.objects.create(name='Reorder Test Medicine', barcode='993130030', price='5.00', cost='3.00')
        self.other_med = Medicine.objects.create(name='Other Pharmacy Only', barcode='993130031', price='5.00', cost='3.00')
        self.healthy_med = Medicine.objects.create(name='Healthy Test Medicine', barcode='993130032', price='5.00', cost='3.00')
        self.supplier = Supplier.objects.create(name='Test Supplier', phone='12345678', email='test@example.com')
        Stock.objects.create(pharmacy=self.beirut, medicine=self.med, quantity=4, reorder_level=10, expiry_date=date(2028,1,1))
        Stock.objects.create(pharmacy=self.other, medicine=self.other_med, quantity=2, reorder_level=10, expiry_date=date(2028,1,1))
        Stock.objects.create(pharmacy=self.beirut, medicine=self.healthy_med, quantity=15, reorder_level=10, expiry_date=date(2028,1,1))
        self.client = APIClient()
        self.payload = {'medicine_id': self.med.id, 'supplier_id': self.supplier.id, 'quantity': 25}

    def test_anonymous_cannot_create_order(self):
        self.assertEqual(self.client.post(self.URL, self.payload, format='json').status_code, 401)
        self.assertEqual(PurchaseOrder.objects.count(), 0)

    def test_pharmacist_cannot_create_order(self):
        self.client.force_authenticate(user=self.pharmacist)
        self.assertEqual(self.client.post(self.URL, self.payload, format='json').status_code, 403)
        self.assertEqual(PurchaseOrder.objects.count(), 0)

    def test_owner_creates_pending_order_without_changing_stock(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(self.URL, self.payload, format='json')
        self.assertEqual(response.status_code, 201)
        order = PurchaseOrder.objects.get()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.pharmacy, self.beirut)
        self.assertEqual(order.quantity, 25)
        self.assertEqual(Stock.objects.get(pharmacy=self.beirut, medicine=self.med).quantity, 4)
        self.assertEqual(response.data['supplier_name'], 'Test Supplier')

    def test_owner_can_place_another_order_for_same_medicine(self):
        self.client.force_authenticate(user=self.owner)
        first = self.client.post(self.URL, self.payload, format='json')
        self.assertEqual(first.status_code, 201)
        second = self.client.post(
            self.URL, {**self.payload, 'quantity': 7}, format='json'
        )
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.data['id'], second.data['id'])
        self.assertEqual(
            list(PurchaseOrder.objects.order_by('id').values_list('quantity', flat=True)),
            [25, 7],
        )
        self.assertTrue(all(
            order.status == 'pending' for order in PurchaseOrder.objects.all()
        ))
        self.assertEqual(
            Stock.objects.get(pharmacy=self.beirut, medicine=self.med).quantity, 4
        )

    def test_owner_can_order_again_while_first_order_is_sent(self):
        self.client.force_authenticate(user=self.owner)
        first = self.client.post(self.URL, self.payload, format='json')
        self.assertEqual(first.status_code, 201)
        PurchaseOrder.objects.filter(pk=first.data['id']).update(status='sent')
        second = self.client.post(
            self.URL, {**self.payload, 'quantity': 3}, format='json'
        )
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.data['id'], second.data['id'])
        self.assertEqual(PurchaseOrder.objects.filter(pharmacy=self.beirut).count(), 2)

    def test_cannot_reorder_medicine_not_stocked_here(self):
        self.client.force_authenticate(user=self.owner)
        payload = {**self.payload, 'medicine_id': self.other_med.id}
        self.assertEqual(self.client.post(self.URL, payload, format='json').status_code, 400)
        self.assertEqual(PurchaseOrder.objects.count(), 0)

    def test_cannot_reorder_healthy_stock(self):
        self.client.force_authenticate(user=self.owner)
        payload = {**self.payload, 'medicine_id': self.healthy_med.id}
        self.assertEqual(self.client.post(self.URL, payload, format='json').status_code, 400)
        self.assertEqual(PurchaseOrder.objects.count(), 0)

    def test_invalid_quantity_rejected(self):
        self.client.force_authenticate(user=self.owner)
        payload = {**self.payload, 'quantity': 0}
        self.assertEqual(self.client.post(self.URL, payload, format='json').status_code, 400)
        self.assertEqual(PurchaseOrder.objects.count(), 0)

    def test_owner_only_sees_own_pharmacy_orders(self):
        order = PurchaseOrder.objects.create(pharmacy=self.other, medicine=self.other_med,
                                              supplier=self.supplier, quantity=20, status='pending')
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
        self.client.force_authenticate(user=self.other_owner)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['id'], order.id)

    def test_supplier_list_requires_owner(self):
        self.client.force_authenticate(user=self.pharmacist)
        self.assertEqual(self.client.get(self.SUPPLIERS).status_code, 403)
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.SUPPLIERS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['name'], 'Test Supplier')
