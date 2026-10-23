from django.contrib import admin
from .models import DailySales, StockAlert, Supplier, PurchaseOrder


@admin.register(DailySales)
class DailySalesAdmin(admin.ModelAdmin):
    list_display = ('date', 'pharmacy', 'medicine', 'quantity_sold')
    list_filter = ('pharmacy', 'medicine')


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