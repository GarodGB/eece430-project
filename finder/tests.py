from datetime import date, timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Pharmacy, User
from finder.views import distance_km
from inventory.models import Medicine, Stock


class DistanceFormulaTests(TestCase):

    def test_known_distance_hamra_to_achrafieh(self):
        self.assertAlmostEqual(distance_km(33.8963, 35.4823, 33.8886, 35.5196), 3.5, delta=0.2)

    def test_same_place_is_zero(self):
        self.assertEqual(distance_km(33.9, 35.5, 33.9, 35.5), 0.0)

    def test_missing_location_gives_none(self):
        self.assertIsNone(distance_km(None, 35.5, 33.9, 35.5))


class FinderDistanceTests(TestCase):
    """PHAR-10: Finder shows distance and phone, nearest pharmacy first."""

    def setUp(self):
        self.home = Pharmacy.objects.create(name="Home", address="Hamra", phone="01 100 001",
                                            latitude=33.8963, longitude=35.4823, shares_stock=True)
        self.far = Pharmacy.objects.create(name="Far", address="Tripoli", phone="06 100 009",
                                           latitude=34.4367, longitude=35.8497, shares_stock=True)
        self.near = Pharmacy.objects.create(name="Near", address="Achrafieh", phone="01 100 002",
                                            latitude=33.8886, longitude=35.5196, shares_stock=True)
        self.no_location = Pharmacy.objects.create(name="Unknown", address="?", phone="01 100 099",
                                                   shares_stock=True)
        self.private = Pharmacy.objects.create(name="Private", address="Verdun", phone="01 100 003",
                                               latitude=33.8851, longitude=35.4826, shares_stock=False)
        medicine = Medicine.objects.create(name="Panadol", barcode="6000001", price="4.00", cost="2.00")
        expiry = date.today() + timedelta(days=100)
        for pharmacy in (self.home, self.far, self.near, self.no_location, self.private):
            Stock.objects.create(pharmacy=pharmacy, medicine=medicine, quantity=10, expiry_date=expiry)

        user = User.objects.create_user("finderuser", password="TestPassword123!",
                                        role="pharmacist", pharmacy=self.home)
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        self.results = self.client.get("/api/finder/?q=panadol").data

    def test_nearest_first_and_unknown_location_last(self):
        names = [row["pharmacy"]["name"] for row in self.results]
        self.assertEqual(names, ["Near", "Far", "Unknown"])

    def test_distance_and_phone_are_shown(self):
        near = self.results[0]
        self.assertAlmostEqual(near["distance_km"], 3.5, delta=0.2)
        self.assertEqual(near["pharmacy"]["phone"], "01 100 002")
        self.assertIsNone(self.results[-1]["distance_km"])

    def test_privacy_rules_still_apply(self):
        names = [row["pharmacy"]["name"] for row in self.results]
        self.assertNotIn("Home", names)
        self.assertNotIn("Private", names)
        self.assertNotIn("quantity", self.results[0])
