from django.contrib import admin
from .models import InsuranceClaim


@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'insurer', 'patient_name', 'amount', 'status', 'submitted_at')
    list_filter = ('status', 'insurer')