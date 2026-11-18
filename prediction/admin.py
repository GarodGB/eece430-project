from django.contrib import admin
from .models import DailySales, StockAlert, Supplier, PurchaseOrder


# Daily sales are filled in automatically by every sale (PHAR-11),
# and the run-out prediction learns from them. In /admin they are READ-ONLY,
# so the history can't be changed by hand.
@admin.register(DailySales)
class DailySalesAdmin(admin.ModelAdmin):
    list_display = ('date', 'pharmacy', 'medicine', 'quantity_sold')
    list_filter = ('pharmacy', 'medicine')
    date_hierarchy = 'date'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ('stock', 'predicted_run_out_date', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email')
    search_fields = ('name',)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'quantity', 'supplier', 'pharmacy', 'status', 'created_at')
    list_filter = ('status', 'pharmacy')