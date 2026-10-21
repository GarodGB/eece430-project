from django.contrib import admin
from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'pharmacy', 'sold_by', 'payment_method', 'total', 'created_at')
    list_filter = ('pharmacy', 'payment_method')
    inlines = [SaleItemInline]