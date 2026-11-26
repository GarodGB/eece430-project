from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Pharmacy, User
from inventory.models import Medicine, Stock
from sales.models import Sale

from .models import DamanStatement, InsuranceClaim, daman_share

DAMAN_URL = '/api/insurance/daman/'
STATEMENTS_URL = '/api/insurance/daman/statements/'


class DamanTestBase(TestCase):
    def setUp(self):
        self.pharmacy = Pharmacy.objects.create(name="Daman Pharmacy", address="Beirut", phone="01 100 100")
        self.other = Pharmacy.objects.create(name="Other Pharmacy", address="Baabda", phone="05 100 100")
        self.pharmacist = User.objects.create_user(username="damanpharmacist", password="TestPassword123!",
                                                   role="pharmacist", pharmacy=self.pharmacy)
        self.owner = User.objects.create_user(username="damanowner", password="TestPassword123!",
                                              role="owner", pharmacy=self.pharmacy)
        self.other_user = User.objects.create_user(username="otherpharmacist", password="TestPassword123!",
                                                   role="pharmacist", pharmacy=self.other)
        self.panadol = Medicine.objects.create(name="Panadol", barcode="8400001", price="25.00", cost="10.00")
        self.augmentin = Medicine.objects.create(name="Augmentin", barcode="8400002", price="12.35",
                                                 cost="5.00", needs_prescription=True)
        expiry = date.today() + timedelta(days=200)
        for pharmacy in (self.pharmacy, self.other):
            Stock.objects.create(pharmacy=pharmacy, medicine=self.panadol, quantity=50, expiry_date=expiry)
            Stock.objects.create(pharmacy=pharmacy, medicine=self.augmentin, quantity=50, expiry_date=expiry)
        self.client = APIClient()
        self.client.force_authenticate(user=self.pharmacist)

    def sell(self, quantity=2, payment='insurance', number='1234567', **extra):
        body = {'payment_method': payment, 'items': [{'barcode': '8400001', 'quantity': quantity}], **extra}
        if number is not None:
            body['daman_number'] = number
        return self.client.post('/api/sales/', body, format='json')


class DamanSaleTests(DamanTestBase):
    """A Daman sale: the customer pays 20% now, Daman owes 80%."""

    def test_daman_sale_creates_an_unpaid_claim_for_80_percent(self):
        response = self.sell()  # 2 x 25.00 = 50.00
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['daman'], {
            'daman_number': '1234567', 'daman_pays': '40.00', 'customer_pays': '10.00',
        })
        claim = InsuranceClaim.objects.get(sale_id=response.data['id'])
        self.assertEqual((claim.amount, claim.status, claim.insurer), (Decimal('40.00'), 'unpaid', 'Daman'))

    def test_daman_share_is_after_discount(self):
        response = self.sell(discount_percent='10')  # 50.00 - 10% = 45.00
        self.assertEqual(response.data['daman']['daman_pays'], '36.00')
        self.assertEqual(response.data['daman']['customer_pays'], '9.00')

    def test_cents_always_add_up(self):
        response = self.client.post('/api/sales/', {
            'payment_method': 'insurance', 'daman_number': '42',
            'prescription_confirmed': True, 'items': [{'barcode': '8400002', 'quantity': 1}],
        }, format='json')  # 12.35 -> Daman 9.88, customer 2.47
        daman = response.data['daman']
        self.assertEqual((daman['daman_pays'], daman['customer_pays']), ('9.88', '2.47'))
        self.assertEqual(Decimal(daman['daman_pays']) + Decimal(daman['customer_pays']), Decimal('12.35'))

    def test_cash_and_card_sales_have_no_claim(self):
        for payment in ('cash', 'card'):
            response = self.sell(payment=payment, number=None)
            self.assertEqual(response.status_code, 201)
            self.assertIsNone(response.data['daman'])
        self.assertEqual(InsuranceClaim.objects.count(), 0)

    def test_daman_number_is_required(self):
        for number in (None, ''):
            response = self.sell(number=number)
            self.assertEqual(response.status_code, 400, number)
            self.assertIn('Daman number', str(response.data))
        self.assertEqual(Sale.objects.count(), 0)

    def test_patient_name_is_not_needed_or_returned(self):
        response = self.sell()
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('patient_name', response.data['daman'])

    def test_daman_number_is_digits_only(self):
        for number in ['12a45', '-123', '12.5', '12 34']:
            self.assertEqual(self.sell(number=number).status_code, 400, number)
        self.assertEqual(Sale.objects.count(), 0)

    def test_failed_daman_sale_saves_nothing(self):
        self.sell(quantity=999)  # not enough stock
        self.assertEqual((Sale.objects.count(), InsuranceClaim.objects.count()), (0, 0))

    def test_share_helper(self):
        self.assertEqual(daman_share(Decimal('50.00')), Decimal('40.00'))
        self.assertEqual(daman_share(Decimal('0.01')), Decimal('0.01'))


class DamanStatementTests(DamanTestBase):
    """Unpaid claims -> printed statement -> marked as paid."""

    def make_claims(self, count=3):
        for _ in range(count):
            self.assertEqual(self.sell().status_code, 201)

    def test_overview_shows_totals_and_unpaid_claims(self):
        self.make_claims(2)
        data = self.client.get(DAMAN_URL).data
        self.assertEqual(data['daman_share_percent'], '80')
        self.assertEqual(data['totals']['unpaid'], {'count': 2, 'amount': '80.00'})
        self.assertEqual(data['totals']['paid'], {'count': 0, 'amount': '0.00'})
        self.assertEqual(len(data['unpaid_claims']), 2)
        self.assertEqual(data['unpaid_claims'][0]['daman_number'], '1234567')

    def test_create_statement_takes_all_unpaid_claims(self):
        self.make_claims(3)
        response = self.client.post(STATEMENTS_URL)
        self.assertEqual(response.status_code, 201)
        self.assertEqual((response.data['number'], response.data['status'], response.data['total']), (1, 'sent', '120.00'))
        self.assertEqual(len(response.data['claims']), 3)
        self.assertEqual(InsuranceClaim.objects.filter(status='sent').count(), 3)
        self.assertEqual(self.client.get(DAMAN_URL).data['unpaid_claims'], [])

    def test_no_unpaid_claims_means_no_statement(self):
        response = self.client.post(STATEMENTS_URL)
        self.assertEqual(response.status_code, 400)
        self.assertIn('no unpaid Daman claims', str(response.data))
        self.assertEqual(DamanStatement.objects.count(), 0)

    def test_second_statement_only_takes_new_claims(self):
        self.make_claims(2)
        self.client.post(STATEMENTS_URL)
        self.make_claims(1)
        second = self.client.post(STATEMENTS_URL).data
        self.assertEqual((second['number'], len(second['claims']), second['total']), (2, 1, '40.00'))

    def test_statement_detail_for_printing(self):
        self.make_claims(2)
        statement_id = self.client.post(STATEMENTS_URL).data['id']
        data = self.client.get(f'{STATEMENTS_URL}{statement_id}/').data
        self.assertEqual(data['pharmacy_name'], 'Daman Pharmacy')
        self.assertEqual(data['claims_count'], 2)
        claim = data['claims'][0]
        for key in ('sale_id', 'sale_date', 'daman_number', 'sale_total', 'daman_pays'):
            self.assertIn(key, claim)

    def test_mark_paid_pays_statement_and_its_claims(self):
        self.make_claims(2)
        statement_id = self.client.post(STATEMENTS_URL).data['id']
        response = self.client.post(f'{STATEMENTS_URL}{statement_id}/mark-paid/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'paid')
        self.assertEqual(response.data['paid_by'], 'damanpharmacist')
        self.assertIsNotNone(response.data['paid_at'])
        self.assertEqual(InsuranceClaim.objects.filter(status='paid').count(), 2)
        self.assertEqual(self.client.get(DAMAN_URL).data['totals']['paid'], {'count': 2, 'amount': '80.00'})

    def test_cannot_mark_paid_twice(self):
        self.make_claims(1)
        statement_id = self.client.post(STATEMENTS_URL).data['id']
        self.client.post(f'{STATEMENTS_URL}{statement_id}/mark-paid/')
        response = self.client.post(f'{STATEMENTS_URL}{statement_id}/mark-paid/')
        self.assertEqual(response.status_code, 400)
        self.assertIn('already marked as paid', str(response.data))

    def test_statements_list_newest_first(self):
        self.make_claims(1)
        self.client.post(STATEMENTS_URL)
        self.make_claims(1)
        self.client.post(STATEMENTS_URL)
        rows = self.client.get(STATEMENTS_URL).data
        self.assertEqual([r['number'] for r in rows], [2, 1])
        self.assertEqual(rows[0]['claims_count'], 1)

    def test_owner_can_use_it_too(self):
        self.make_claims(1)
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.post(STATEMENTS_URL).status_code, 201)

    def test_other_pharmacy_sees_nothing_and_cannot_touch(self):
        self.make_claims(2)
        statement_id = self.client.post(STATEMENTS_URL).data['id']
        self.client.force_authenticate(user=self.other_user)
        self.assertEqual(self.client.get(DAMAN_URL).data['totals']['sent']['count'], 0)
        self.assertEqual(self.client.get(STATEMENTS_URL).data, [])
        self.assertEqual(self.client.get(f'{STATEMENTS_URL}{statement_id}/').status_code, 404)
        self.assertEqual(self.client.post(f'{STATEMENTS_URL}{statement_id}/mark-paid/').status_code, 404)
        self.assertEqual(self.client.post(STATEMENTS_URL).status_code, 400)  # it has no claims of its own
        self.assertEqual(DamanStatement.objects.get(pk=statement_id).status, 'sent')

    def test_not_logged_in_or_no_pharmacy_is_refused(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(DAMAN_URL).status_code, 401)
        admin = User.objects.create_superuser(username="damanadmin", password="TestPassword123!", role="admin")
        self.client.force_authenticate(user=admin)
        self.assertEqual(self.client.get(DAMAN_URL).status_code, 403)


class DamanAdminReadOnlyTests(DamanTestBase):
    def test_admin_can_view_but_not_change(self):
        self.sell()
        self.client.post(STATEMENTS_URL)
        admin = User.objects.create_superuser(username="damanadmin2", password="TestPassword123!", role="admin")
        self.client.force_login(admin)
        for url in ('/admin/insurance/insuranceclaim/', '/admin/insurance/damanstatement/'):
            self.assertEqual(self.client.get(url).status_code, 200)
            self.assertEqual(self.client.get(url + 'add/').status_code, 403)
        claim = InsuranceClaim.objects.get()
        self.client.post(f'/admin/insurance/insuranceclaim/{claim.id}/change/', {'amount': '1.00'})
        claim.refresh_from_db()
        self.assertEqual(claim.amount, Decimal('40.00'))
