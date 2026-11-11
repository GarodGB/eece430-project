from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Pharmacy, User
from inventory.models import Medicine, Stock
from sales.models import Sale


class SaleDiscountTests(TestCase):
    """Whole-receipt discount in percent; never below cost."""

    def setUp(self):
        self.pharmacy = Pharmacy.objects.create(name="Sale Pharmacy", address="Beirut", phone="11111111")
        self.user = User.objects.create_user(
            username="salepharmacist", password="TestPassword123!",
            role="pharmacist", pharmacy=self.pharmacy,
        )
        # Example from the design: 2 x Panadol (4.00, cost 2.00) + 1 x Brufen (5.00, cost 3.00)
        # subtotal 13.00, cost 7.00, maximum discount 46.15%
        self.panadol = Medicine.objects.create(name="Panadol", barcode="8000001", price="4.00", cost="2.00")
        self.brufen = Medicine.objects.create(name="Brufen", barcode="8000002", price="5.00", cost="3.00")
        expiry = date.today() + timedelta(days=200)
        self.panadol_stock = Stock.objects.create(pharmacy=self.pharmacy, medicine=self.panadol,
                                                  quantity=10, expiry_date=expiry)
        self.brufen_stock = Stock.objects.create(pharmacy=self.pharmacy, medicine=self.brufen,
                                                 quantity=10, expiry_date=expiry)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def sell(self, discount=None):
        body = {"items": [{"barcode": "8000001", "quantity": 2}, {"barcode": "8000002", "quantity": 1}]}
        if discount is not None:
            body["discount_percent"] = discount
        return self.client.post("/api/sales/", body, format="json")

    def test_no_discount_total_equals_subtotal(self):
        response = self.sell()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["subtotal"], "13.00")
        self.assertEqual(response.data["discount_percent"], "0.00")
        self.assertEqual(response.data["total"], "13.00")

    def test_ten_percent_discount(self):
        response = self.sell("10")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["subtotal"], "13.00")
        self.assertEqual(response.data["total"], "11.70")

    def test_maximum_discount_is_allowed(self):
        response = self.sell("46.15")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["total"], "7.00")

    def test_discount_below_cost_is_blocked_with_max_shown(self):
        response = self.sell("50")
        self.assertEqual(response.status_code, 400)
        self.assertIn("below cost", str(response.data))
        self.assertIn("46.15%", str(response.data))

    def test_blocked_discount_changes_nothing(self):
        self.sell("50")
        self.panadol_stock.refresh_from_db()
        self.brufen_stock.refresh_from_db()
        self.assertEqual(self.panadol_stock.quantity, 10)
        self.assertEqual(self.brufen_stock.quantity, 10)
        self.assertEqual(Sale.objects.count(), 0)

    def test_discount_over_100_or_negative_is_rejected(self):
        self.assertEqual(self.sell("150").status_code, 400)
        self.assertEqual(self.sell("-5").status_code, 400)

    def test_cost_is_not_sent_back(self):
        response = self.sell("10")
        self.assertNotIn("unit_cost", response.data["items"][0])

    def test_unit_cost_is_saved_for_reports(self):
        self.sell("10")
        line = Sale.objects.get().items.get(medicine=self.panadol)
        self.assertEqual(str(line.unit_cost), "2.00")


class MedicinePriceRuleTests(TestCase):

    def test_price_lower_than_cost_is_blocked(self):
        medicine = Medicine(name="Bad", barcode="7000001", price="5.00", cost="10.00")
        with self.assertRaises(ValidationError):
            medicine.full_clean()

    def test_price_equal_or_above_cost_is_allowed(self):
        Medicine(name="Ok", barcode="7000002", price="5.00", cost="5.00").full_clean()
        Medicine(name="Ok2", barcode="7000003", price="6.00", cost="5.00").full_clean()
