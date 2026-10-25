from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError 


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
        ('admin', 'System admin'),
        ('owner', 'Owner'),
        ('pharmacist', 'Pharmacist'),
        ('assistant', 'Assistant'),
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

   