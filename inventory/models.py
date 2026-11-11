from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from accounts.models import Pharmacy


class Medicine(models.Model):
    name = models.CharField(max_length=100)
    generic_name = models.CharField(max_length=100, blank=True)
    barcode = models.CharField(
        max_length=50,
        unique=True,
        validators=[RegexValidator(r'^\d+$', 'Barcode must contain digits only.')],
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), 'Price must be greater than 0.')],
    )
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'), "Cost can't be negative.")],
    )
    needs_prescription = models.BooleanField(default=False)

    def clean(self):
        # The selling price can't be lower than the buying price.
        if self.price is not None and self.cost is not None and self.cost > self.price:
            raise ValidationError({'price': "Price can't be lower than cost."})

    def __str__(self):
        return self.name


class Stock(models.Model):
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField()
    reorder_level = models.PositiveIntegerField(default=10)

    def clean(self):
        # Only block NEW stock that is already expired.
        # Old stock that expired later can still be edited (e.g. to fix its quantity).
        if self._state.adding and self.expiry_date and self.expiry_date < date.today():
            raise ValidationError({'expiry_date': "Can't add stock that is already expired."})

    def __str__(self):
        return f"{self.medicine} at {self.pharmacy}: {self.quantity}"