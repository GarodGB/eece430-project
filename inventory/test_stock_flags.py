from datetime import date, timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Pharmacy, User
from inventory.models import Medicine, Stock


class StockFlagTests(TestCase):
    """Low stock is checked per medicine (all valid batches), and expired stock has its own flag."""

    def setUp(self):
        self.pharmacy = Pharmacy.objects.create(name="Flag Pharmacy", address="Beirut", phone="11111111")
        self.other = Pharmacy.objects.create(name="Other Pharmacy", address="Baabda", phone="22222222")
        self.user = User.objects.create_user(
            username="flagpharmacist", password="TestPassword123!",
            role="pharmacist", pharmacy=self.pharmacy,
        )
        self.panadol = Medicine.objects.create(name="Panadol", barcode="9000001", price="4.00", cost="2.00")
        today = date.today()

        # Panadol: 5 + 40 valid boxes = 45 total, plus 7 expired boxes that must not count.
        self.small_batch = Stock.objects.create(pharmacy=self.pharmacy, medicine=self.panadol,
                                                quantity=5, reorder_level=10, expiry_date=today + timedelta(days=200))
        self.big_batch = Stock.objects.create(pharmacy=self.pharmacy, medicine=self.panadol,
                                              quantity=40, reorder_level=10, expiry_date=today + timedelta(days=400))
        self.expired_batch = Stock.objects.create(pharmacy=self.pharmacy, medicine=self.panadol,
                                                  quantity=7, reorder_level=10, expiry_date=today - timedelta(days=10))
        self.soon_batch = Stock.objects.create(pharmacy=self.pharmacy, medicine=Medicine.objects.create(
            name="Brufen", barcode="9000002", price="5.00", cost="3.00"),
            quantity=3, reorder_level=10, expiry_date=today + timedelta(days=15))

        # Another pharmacy's Panadol must not be added to our total.
        Stock.objects.create(pharmacy=self.other, medicine=self.panadol,
                             quantity=100, reorder_level=10, expiry_date=today + timedelta(days=300))

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.rows = {row["id"]: row for row in self.client.get("/api/stock/").data}

    def test_small_batch_not_low_when_total_is_enough(self):
        row = self.rows[self.small_batch.id]
        self.assertEqual(row["total_quantity"], 45)
        self.assertFalse(row["is_low"])

    def test_total_ignores_expired_batches_and_other_pharmacies(self):
        self.assertEqual(self.rows[self.big_batch.id]["total_quantity"], 45)

    def test_low_when_total_is_below_reorder_level(self):
        row = self.rows[self.soon_batch.id]
        self.assertEqual(row["total_quantity"], 3)
        self.assertTrue(row["is_low"])

    def test_expired_batch_has_expired_flag_not_expiring_soon(self):
        row = self.rows[self.expired_batch.id]
        self.assertTrue(row["is_expired"])
        self.assertFalse(row["expiring_soon"])

    def test_expiring_soon_only_for_stock_not_yet_expired(self):
        row = self.rows[self.soon_batch.id]
        self.assertTrue(row["expiring_soon"])
        self.assertFalse(row["is_expired"])