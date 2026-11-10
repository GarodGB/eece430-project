
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import Pharmacy, User
from inventory.models import Medicine


class MedicineSearchTests(TestCase):

    def setUp(self):
        # Create a fictional pharmacy for testing
        self.pharmacy = Pharmacy.objects.create(
            name="Test Pharmacy",
            address="Beirut",
            phone="00000000"
        )

        # Create a test pharmacist
        self.user = User.objects.create_user(
            username="testpharmacist",
            password="TestPassword123!",
            role="pharmacist",
            pharmacy=self.pharmacy
        )

        # Create test medicines
        self.panadol = Medicine.objects.create(
            name="Panadol 500mg",
            generic_name="Paracetamol",
            barcode="1234567890001",
            price="3.50",
            cost="2.00"
        )

        self.brufen = Medicine.objects.create(
            name="Brufen 400mg",
            generic_name="Ibuprofen",
            barcode="1234567890002",
            price="4.00",
            cost="2.50"
        )

        # Authenticate the test client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    # Test 1: Search by medicine name
    def test_search_by_name(self):
        response = self.client.get(
            "/api/medicines/?search=Panadol"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["name"], "Panadol 500mg"
        )

    # Test 2: Search by generic name
    def test_search_by_generic_name(self):
        response = self.client.get(
            "/api/medicines/?search=Paracetamol"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["name"], "Panadol 500mg"
        )

    # Test 3: Search by barcode
    def test_search_by_barcode(self):
        response = self.client.get(
            "/api/medicines/?search=1234567890002"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["name"], "Brufen 400mg"
        )

    # Test 4: Case-insensitive search
    def test_case_insensitive_search(self):
        response = self.client.get(
            "/api/medicines/?search=PANADOL"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    # Test 5: Medicine does not exist
    def test_nonexistent_medicine(self):
        response = self.client.get(
            "/api/medicines/?search=NonexistentMedicine"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    # Test 6: Unauthenticated access
    def test_search_without_login(self):
        anonymous_client = APIClient()

        response = anonymous_client.get(
            "/api/medicines/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

from datetime import date, timedelta
from inventory.models import Stock


class StockManagementTests(TestCase):

    def setUp(self):
        self.pharmacy1 = Pharmacy.objects.create(
            name="Beirut Test Pharmacy",
            address="Beirut",
            phone="11111111"
        )
        self.pharmacy2 = Pharmacy.objects.create(
            name="Baabda Test Pharmacy",
            address="Baabda",
            phone="22222222"
        )

        self.pharmacist = User.objects.create_user(
            username="stockpharmacist",
            password="TestPassword123!",
            role="pharmacist",
            pharmacy=self.pharmacy1
        )

        self.admin = User.objects.create_superuser(
            username="stockadmin",
            password="TestPassword123!"
        )

        medicine1 = Medicine.objects.create(
            name="Test Medicine A",
            barcode="STOCK001",
            price="5.00",
            cost="3.00"
        )
        medicine2 = Medicine.objects.create(
            name="Test Medicine B",
            barcode="STOCK002",
            price="6.00",
            cost="4.00"
        )

        self.low_stock = Stock.objects.create(
            pharmacy=self.pharmacy1,
            medicine=medicine1,
            quantity=4,
            reorder_level=10,
            expiry_date=date.today() + timedelta(days=15)
        )

        self.normal_stock = Stock.objects.create(
            pharmacy=self.pharmacy1,
            medicine=medicine2,
            quantity=20,
            reorder_level=10,
            expiry_date=date.today() + timedelta(days=90)
        )

        self.other_stock = Stock.objects.create(
            pharmacy=self.pharmacy2,
            medicine=medicine1,
            quantity=8,
            reorder_level=10,
            expiry_date=date.today() + timedelta(days=60)
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.pharmacist)

    # Test 1: Pharmacist can see their pharmacy's stock
    def test_pharmacist_can_view_own_stock(self):
        response = self.client.get("/api/stock/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

        returned_ids = {item["id"] for item in response.data}
        self.assertIn(self.low_stock.id, returned_ids)
        self.assertIn(self.normal_stock.id, returned_ids)

    # Test 2: Pharmacist cannot see another pharmacy's stock
    def test_pharmacist_cannot_view_other_stock(self):
        response = self.client.get("/api/stock/")

        returned_ids = {item["id"] for item in response.data}
        self.assertNotIn(self.other_stock.id, returned_ids)

    # Test 3: System admin can see all pharmacies' stock
    def test_admin_can_view_all_stock(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/stock/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

    # Test 4: Low-stock detection
    def test_low_stock_detection(self):
        response = self.client.get("/api/stock/")

        results = {item["id"]: item for item in response.data}

        self.assertTrue(results[self.low_stock.id]["is_low"])
        self.assertFalse(results[self.normal_stock.id]["is_low"])

    # Test 5: Expiring-soon detection
    def test_expiring_soon_detection(self):
        response = self.client.get("/api/stock/")

        results = {item["id"]: item for item in response.data}

        self.assertTrue(
            results[self.low_stock.id]["expiring_soon"]
        )
        self.assertFalse(
            results[self.normal_stock.id]["expiring_soon"]
        )

    # Test 6: Unauthenticated users cannot see stock
    def test_stock_requires_authentication(self):
        anonymous_client = APIClient()

        response = anonymous_client.get("/api/stock/")

        self.assertEqual(response.status_code, 401)
