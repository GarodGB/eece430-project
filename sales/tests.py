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


class PrescriptionCheckTests(TestCase):
    """A medicine that needs a prescription can't be sold until the pharmacist confirms it."""

    def setUp(self):
        self.pharmacy = Pharmacy.objects.create(name="Rx Pharmacy", address="Beirut", phone="11111111")
        self.user = User.objects.create_user(
            username="rxpharmacist", password="TestPassword123!",
            role="pharmacist", pharmacy=self.pharmacy,
        )
        self.augmentin = Medicine.objects.create(name="Augmentin", barcode="8100001", price="12.00",
                                                 cost="8.00", needs_prescription=True)
        self.panadol = Medicine.objects.create(name="Panadol", barcode="8100002", price="4.00", cost="2.00")
        expiry = date.today() + timedelta(days=200)
        self.augmentin_stock = Stock.objects.create(pharmacy=self.pharmacy, medicine=self.augmentin,
                                                    quantity=10, expiry_date=expiry)
        Stock.objects.create(pharmacy=self.pharmacy, medicine=self.panadol, quantity=10, expiry_date=expiry)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def sell(self, barcodes, confirmed=None):
        body = {"items": [{"barcode": code, "quantity": 1} for code in barcodes]}
        if confirmed is not None:
            body["prescription_confirmed"] = confirmed
        return self.client.post("/api/sales/", body, format="json")

    def test_prescription_medicine_blocked_without_confirmation(self):
        response = self.sell(["8100001"])
        self.assertEqual(response.status_code, 400)
        self.assertIn("Augmentin needs a prescription", str(response.data))

    def test_blocked_sale_changes_nothing(self):
        self.sell(["8100002", "8100001"])  # Panadol first, then the blocked Augmentin
        self.assertEqual(Sale.objects.count(), 0)
        self.augmentin_stock.refresh_from_db()
        self.assertEqual(self.augmentin_stock.quantity, 10)

    def test_prescription_medicine_sold_when_confirmed(self):
        response = self.sell(["8100001"], confirmed=True)
        self.assertEqual(response.status_code, 201)
        self.augmentin_stock.refresh_from_db()
        self.assertEqual(self.augmentin_stock.quantity, 9)

    def test_normal_medicine_needs_no_confirmation(self):
        self.assertEqual(self.sell(["8100002"]).status_code, 201)


class SaleAdminReadOnlyTests(TestCase):
    """In /admin, sales can be viewed but not added, edited or deleted."""

    def setUp(self):
        self.admin = User.objects.create_superuser(username="sysadmin", password="TestPassword123!",
                                                   role="admin")
        pharmacy = Pharmacy.objects.create(name="Admin Pharmacy", address="Beirut", phone="11111111")
        self.sale = Sale.objects.create(pharmacy=pharmacy, total="10.00", subtotal="10.00")
        self.client.force_login(self.admin)

    def test_admin_can_view_sales(self):
        self.assertEqual(self.client.get("/admin/sales/sale/").status_code, 200)
        self.assertEqual(self.client.get(f"/admin/sales/sale/{self.sale.id}/change/").status_code, 200)

    def test_admin_cannot_add_sales(self):
        self.assertEqual(self.client.get("/admin/sales/sale/add/").status_code, 403)

    def test_admin_cannot_edit_sales(self):
        self.client.post(f"/admin/sales/sale/{self.sale.id}/change/", {"total": "0.01"})
        self.sale.refresh_from_db()
        self.assertEqual(str(self.sale.total), "10.00")

    def test_admin_cannot_delete_sales(self):
        self.client.post(f"/admin/sales/sale/{self.sale.id}/delete/", {"post": "yes"})
        self.assertTrue(Sale.objects.filter(pk=self.sale.pk).exists())
