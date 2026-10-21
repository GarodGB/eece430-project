from django.db import models
from accounts.models import Pharmacy


class Medicine(models.Model):
    name = models.CharField(max_length=100)
    generic_name = models.CharField(max_length=100, blank=True)
    barcode = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    needs_prescription = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Stock(models.Model):
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField()
    reorder_level = models.PositiveIntegerField(default=10)

    def __str__(self):
        return f"{self.medicine} at {self.pharmacy}: {self.quantity}"