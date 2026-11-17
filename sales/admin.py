from django.contrib import admin
from .models import Sale, SaleItem


# Sales are created only by the Point of Sale.
# In /admin they are READ-ONLY: the admin can look, but can't add, edit or delete,
# so the sales history (and the reports built on it) can't be changed by hand.

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    fields = ('medicine', 'quantity', 'unit_price', 'unit_cost')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'pharmacy', 'sold_by', 'payment_method', 'subtotal',
                    'discount_percent', 'total', 'created_at')
    list_filter = ('pharmacy', 'payment_method')
    inlines = [SaleItemInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
