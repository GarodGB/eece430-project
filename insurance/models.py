from django.db import models
from sales.models import Sale


class InsuranceClaim(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]
    sale = models.OneToOneField(Sale, on_delete=models.PROTECT, related_name='claim')
    insurer = models.CharField(max_length=100)
    patient_name = models.CharField(max_length=100)
    policy_number = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Claim #{self.id} - {self.insurer} - {self.status}"