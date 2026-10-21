from django.db import models
from django.contrib.auth.models import AbstractUser


class Pharmacy(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    shares_stock = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Pharmacies'

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('pharmacist', 'Pharmacist'),
        ('assistant', 'Assistant'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='pharmacist')
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
