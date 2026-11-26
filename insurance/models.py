from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models

from accounts.models import Pharmacy
from sales.models import Sale

# PHAR-16: Daman (Lebanon's national social security) is the only insurer.
# It always approves and always pays the same fixed share of an insured sale.
DAMAN = 'Daman'
DAMAN_SHARE_PERCENT = Decimal('80')


def daman_share(total):
    """Daman's part of a sale total (80%), rounded to the cent."""
    return (Decimal(total) * DAMAN_SHARE_PERCENT / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class DamanStatement(models.Model):
    """A printed list of unpaid claims that the pharmacy takes to Daman to get paid."""
    SENT = 'sent'
    PAID = 'paid'
    STATUS_CHOICES = [
        (SENT, 'Sent to Daman'),
        (PAID, 'Paid'),
    ]
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.PROTECT, related_name='daman_statements')
    # Statement number inside the pharmacy: 1, 2, 3...
    number = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=SENT)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='+')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['pharmacy', 'number'], name='unique_statement_number_per_pharmacy'),
        ]
        ordering = ['-number']

    def __str__(self):
        return f"Daman statement #{self.number} - {self.pharmacy} - {self.get_status_display()}"


class InsuranceClaim(models.Model):
    """What Daman owes the pharmacy for one sale."""
    UNPAID = 'unpaid'
    SENT = 'sent'
    PAID = 'paid'
    STATUS_CHOICES = [
        (UNPAID, 'Unpaid'),
        (SENT, 'Sent to Daman'),
        (PAID, 'Paid'),
    ]
    sale = models.OneToOneField(Sale, on_delete=models.PROTECT, related_name='claim')
    insurer = models.CharField(max_length=100, default=DAMAN)
    # Not used any more: a Daman claim only needs the patient's Daman number.
    patient_name = models.CharField(max_length=100, blank=True, default='')
    policy_number = models.CharField('Daman number', max_length=50)
    # Daman's share (80% of the sale total).
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=UNPAID)
    submitted_at = models.DateTimeField(auto_now_add=True)
    statement = models.ForeignKey(DamanStatement, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name='claims')

    class Meta:
        ordering = ['-sale__created_at']

    @property
    def customer_paid(self):
        return self.sale.total - self.amount

    def __str__(self):
        return f"Claim #{self.id} - {self.insurer} - {self.status}"
