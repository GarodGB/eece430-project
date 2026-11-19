from django.contrib import admin
from .models import Medicine, Stock, MedicineReservation


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

@admin.register(MedicineReservation)
class MedicineReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'pharmacy', 'medicine', 'quantity', 'customer_name',
                    'status', 'reserved_by', 'created_at')
    list_filter = ('pharmacy', 'status')
    search_fields = ('customer_name', 'medicine__name')
    readonly_fields = ('pharmacy', 'medicine', 'quantity', 'customer_name',
                       'customer_phone', 'status', 'reserved_by', 'created_at',
                       'released_by', 'released_at', 'request_key')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
