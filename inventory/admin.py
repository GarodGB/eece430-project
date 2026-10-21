from django.contrib import admin
from .models import Medicine, Stock


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'generic_name', 'barcode', 'price', 'cost', 'needs_prescription')
    search_fields = ('name', 'generic_name', 'barcode')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'pharmacy', 'quantity', 'reorder_level', 'is_low', 'expiry_date')
    list_filter = ('pharmacy',)
    search_fields = ('medicine__name',)

    @admin.display(boolean=True, description='Low stock')
    def is_low(self, obj):
        return obj.quantity < obj.reorder_level