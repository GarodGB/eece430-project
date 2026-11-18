"""PHAR-13: low-stock alert API authorization and pharmacy-isolation tests.

Copy into prediction/test_phar13.py; run with Django's normal test runner.
"""
from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Pharmacy, User
from inventory.models import Medicine, Stock


class LowStockAlertAPITests(TestCase):
    URL = "/api/alerts/low-stock/"

    def setUp(self):
        self.beirut = Pharmacy.objects.create(
            name="PHAR13 Test Beirut", address="Beirut", phone="11111111"
        )
        self.achrafieh = Pharmacy.objects.create(
            name="PHAR13 Test Achrafieh", address="Achrafieh", phone="22222222"
        )
        self.beirut_user = User.objects.create_user(
            username="phar13_beirut", password="TestOnly123!",
            role="pharmacist", pharmacy=self.beirut,
        )
        self.achrafieh_user = User.objects.create_user(
            username="phar13_achrafieh", password="TestOnly123!",
            role="pharmacist", pharmacy=self.achrafieh,
        )
        self.med_a = Medicine.objects.create(
            name="PHAR13 Unique Medicine Beirut", barcode="993130001",
            price="5.00", cost="2.00",
        )
        self.med_b = Medicine.objects.create(
            name="PHAR13 Unique Medicine Achrafieh", barcode="993130002",
            price="6.00", cost="3.00",
        )
        Stock.objects.create(
            pharmacy=self.beirut, medicine=self.med_a, quantity=3,
            reorder_level=10, expiry_date=date(2028, 1, 1),
        )
        Stock.objects.create(
            pharmacy=self.achrafieh, medicine=self.med_b, quantity=2,
            reorder_level=8, expiry_date=date(2028, 1, 1),
        )
        self.client = APIClient()

    def test_anonymous_user_cannot_access_alerts(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 401)

    def test_beirut_pharmacist_only_sees_beirut_alert(self):
        self.client.force_authenticate(user=self.beirut_user)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["medicine_id"], self.med_a.id)
        self.assertEqual(response.data[0]["available_quantity"], 3)
        self.assertEqual(response.data[0]["reorder_level"], 10)
        self.assertEqual(response.data[0]["shortfall"], 7)

    def test_achrafieh_pharmacist_only_sees_achrafieh_alert(self):
        self.client.force_authenticate(user=self.achrafieh_user)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["medicine_id"], self.med_b.id)
        self.assertEqual(response.data[0]["available_quantity"], 2)
        self.assertEqual(response.data[0]["shortfall"], 6)

    def test_normal_stock_does_not_trigger_alert(self):
        Stock.objects.filter(pharmacy=self.beirut, medicine=self.med_a).update(quantity=15)
        self.client.force_authenticate(user=self.beirut_user)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
