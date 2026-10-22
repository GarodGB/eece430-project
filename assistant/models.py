from django.db import models
from inventory.models import Medicine


class DrugInfo(models.Model):
    medicine = models.OneToOneField(Medicine, on_delete=models.CASCADE, related_name='info')
    description = models.TextField()
    usual_dose = models.CharField(max_length=200)
    side_effects = models.TextField(blank=True)
    warnings = models.TextField(blank=True)

    def __str__(self):
        return f"Info: {self.medicine}"


class Alternative(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='alternatives')
    alternative = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='alternative_for')
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('medicine', 'alternative')

    def __str__(self):
        return f"{self.alternative} instead of {self.medicine}"