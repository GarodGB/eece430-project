from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import Pharmacy, User


class PharmacyLocationTests(TestCase):
    """A pharmacy's location must be inside Lebanon, with both numbers or neither."""

    def make(self, latitude, longitude):
        return Pharmacy(name="Location Pharmacy", address="Beirut", phone="01 100 100",
                        latitude=latitude, longitude=longitude)

    def test_location_in_lebanon_is_accepted(self):
        self.make(33.8963, 35.4823).full_clean()  # Hamra

    def test_edges_of_the_range_are_accepted(self):
        self.make(33.0, 35.1).full_clean()
        self.make(34.7, 36.7).full_clean()

    def test_no_location_is_accepted(self):
        self.make(None, None).full_clean()

    def test_negative_latitude_is_refused(self):
        with self.assertRaisesMessage(ValidationError, 'Latitude must be between 33.0 and 34.7'):
            self.make(-33.89, 35.48).full_clean()

    def test_latitude_out_of_lebanon_is_refused(self):
        for value in [999, 90, 32.99, 34.71, 0]:
            with self.assertRaises(ValidationError, msg=value) as error:
                self.make(value, 35.48).full_clean()
            self.assertIn('latitude', error.exception.message_dict)

    def test_longitude_out_of_lebanon_is_refused(self):
        for value in [-35.48, 180, 35.09, 36.71, 0]:
            with self.assertRaises(ValidationError, msg=value) as error:
                self.make(33.89, value).full_clean()
            self.assertIn('longitude', error.exception.message_dict)

    def test_swapped_latitude_and_longitude_are_refused(self):
        with self.assertRaises(ValidationError) as error:
            self.make(35.4823, 33.8963).full_clean()
        self.assertIn('latitude', error.exception.message_dict)
        self.assertIn('longitude', error.exception.message_dict)

    def test_only_one_number_is_refused(self):
        for latitude, longitude in [(33.89, None), (None, 35.48)]:
            with self.assertRaisesMessage(ValidationError, 'Enter both latitude and longitude'):
                self.make(latitude, longitude).full_clean()


class PharmacyAdminLocationTests(TestCase):
    """The same rules in the /admin Pharmacy form."""

    def setUp(self):
        admin = User.objects.create_superuser(username="locadmin", password="TestPassword123!", role="admin")
        self.client.force_login(admin)
        self.pharmacy = Pharmacy.objects.create(name="Admin Location Pharmacy", address="Beirut",
                                                phone="01 100 100", latitude=33.8963, longitude=35.4823)
        self.url = f"/admin/accounts/pharmacy/{self.pharmacy.id}/change/"

    def save(self, latitude, longitude):
        return self.client.post(self.url, {
            'name': self.pharmacy.name, 'address': self.pharmacy.address, 'phone': self.pharmacy.phone,
            'latitude': latitude, 'longitude': longitude, 'shares_stock': 'on',
        })

    def assert_not_saved(self, response, message):
        self.assertEqual(response.status_code, 200)  # the form is shown again with an error
        self.assertContains(response, message)
        self.pharmacy.refresh_from_db()
        self.assertEqual((self.pharmacy.latitude, self.pharmacy.longitude), (33.8963, 35.4823))

    def test_valid_location_is_saved(self):
        self.assertEqual(self.save('33.8886', '35.5196').status_code, 302)
        self.pharmacy.refresh_from_db()
        self.assertEqual((self.pharmacy.latitude, self.pharmacy.longitude), (33.8886, 35.5196))

    def test_letters_are_refused(self):
        self.assert_not_saved(self.save('abc', '35.48'), 'Enter a number.')

    def test_negative_is_refused(self):
        self.assert_not_saved(self.save('-50', '35.48'), 'Latitude must be between 33.0 and 34.7')

    def test_too_big_is_refused(self):
        self.assert_not_saved(self.save('33.89', '999'), 'Longitude must be between 35.1 and 36.7')

    def test_not_a_real_number_is_refused(self):
        for value in ['nan', 'inf', '-inf']:
            self.assert_not_saved(self.save(value, '35.48'), 'Enter a number.')

    def test_only_one_number_is_refused(self):
        self.assert_not_saved(self.save('33.89', ''), 'Enter both latitude and longitude')

    def test_clearing_both_is_allowed(self):
        self.assertEqual(self.save('', '').status_code, 302)
        self.pharmacy.refresh_from_db()
        self.assertIsNone(self.pharmacy.latitude)
