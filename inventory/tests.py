
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
