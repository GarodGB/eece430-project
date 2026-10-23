from django.db import models
from accounts.models import Pharmacy
from inventory.models import Medicine, Stock


class DailySales(models.Model):
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    date = models.DateField()
    quantity_sold = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('pharmacy', 'medicine', 'date')
        verbose_name_plural = 'Daily sales'

    def __str__(self):
        return f"{self.medicine} on {self.date}: {self.quantity_sold}"


class StockAlert(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('reordered', 'Reordered'),
        ('closed', 'Closed'),
    ]
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    predicted_run_out_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alert: {self.stock.medicine} runs out {self.predicted_run_out_date}"


class Supplier(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('received', 'Received'),
    ]
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order: {self.quantity} x {self.medicine} from {self.supplier}"