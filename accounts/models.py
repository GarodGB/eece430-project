from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator

# PharmaLink is for pharmacies in Lebanon, so a location must be inside Lebanon.
LEBANON_LATITUDE = (33.0, 34.7)
LEBANON_LONGITUDE = (35.1, 36.7)


class Pharmacy(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^[\d +]+$', 'Phone can only contain digits, spaces and +.')],
    )
    latitude = models.FloatField(
        null=True, blank=True,
        validators=[
            MinValueValidator(LEBANON_LATITUDE[0], 'Latitude must be between 33.0 and 34.7 (inside Lebanon).'),
            MaxValueValidator(LEBANON_LATITUDE[1], 'Latitude must be between 33.0 and 34.7 (inside Lebanon).'),
        ],
    )
    longitude = models.FloatField(
        null=True, blank=True,
        validators=[
            MinValueValidator(LEBANON_LONGITUDE[0], 'Longitude must be between 35.1 and 36.7 (inside Lebanon).'),
            MaxValueValidator(LEBANON_LONGITUDE[1], 'Longitude must be between 35.1 and 36.7 (inside Lebanon).'),
        ],
    )
    shares_stock = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Pharmacies'

    def clean(self):
        # A location needs both numbers, or neither (then distance is shown as unknown).
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError('Enter both latitude and longitude, or leave both empty.')

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'System admin'),
        ('owner', 'Owner'),
        ('pharmacist', 'Pharmacist'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='pharmacist')
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.SET_NULL, null=True, blank=True)

    def clean(self):
        if self.is_superuser and self.pharmacy:
            raise ValidationError("A system admin can't belong to a pharmacy.")
        if not self.is_superuser and not self.pharmacy:
            raise ValidationError("Pharmacy staff must belong to a pharmacy.")
        if self.role == 'admin' and not self.is_superuser:
            raise ValidationError("Only superusers can be System admin.")

    def __str__(self):
        return f"{self.username} ({self.role})"