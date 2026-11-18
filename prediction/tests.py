from datetime import date

from django.test import TestCase

from accounts.models import Pharmacy, User
from inventory.models import Medicine
from prediction.models import DailySales


class DailySalesAdminReadOnlyTests(TestCase):
    """Daily sales come from real sales (PHAR-11), so /admin can view them but not change them."""

    def setUp(self):
        admin = User.objects.create_superuser(username="dailyadmin", password="TestPassword123!", role="admin")
        self.client.force_login(admin)
        pharmacy = Pharmacy.objects.create(name="Daily Pharmacy", address="Beirut", phone="11111111")
        medicine = Medicine.objects.create(name="Panadol", barcode="8300001", price="4.00", cost="2.00")
        self.row = DailySales.objects.create(pharmacy=pharmacy, medicine=medicine,
                                             date=date.today(), quantity_sold=5)
        self.url = f"/admin/prediction/dailysales/{self.row.id}/"

    def test_admin_can_view_daily_sales(self):
        self.assertEqual(self.client.get("/admin/prediction/dailysales/").status_code, 200)
        response = self.client.get(self.url + "change/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="_save"')

    def test_admin_cannot_add(self):
        self.assertEqual(self.client.get("/admin/prediction/dailysales/add/").status_code, 403)

    def test_admin_cannot_edit(self):
        self.client.post(self.url + "change/", {"quantity_sold": 999})
        self.row.refresh_from_db()
        self.assertEqual(self.row.quantity_sold, 5)

    def test_admin_cannot_delete(self):
        self.assertEqual(self.client.post(self.url + "delete/", {"post": "yes"}).status_code, 403)
        self.assertTrue(DailySales.objects.filter(pk=self.row.pk).exists())

    def test_other_prediction_tables_still_editable(self):
        # Only daily sales is locked; suppliers and orders are still managed in /admin.
        self.assertEqual(self.client.get("/admin/prediction/supplier/add/").status_code, 200)
