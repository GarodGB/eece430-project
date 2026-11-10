from datetime import date

from rest_framework import serializers

from .models import Medicine, Stock


class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = ['id', 'name', 'generic_name', 'barcode', 'price', 'needs_prescription']


class StockSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    # Total of all NON-expired batches of this medicine in this pharmacy.
    # Filled in by MyStockView (see inventory/views.py).
    total_quantity = serializers.IntegerField(read_only=True)
    is_low = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    expiring_soon = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = ['id', 'medicine', 'medicine_name', 'quantity', 'total_quantity',
                  'reorder_level', 'expiry_date', 'is_low', 'is_expired', 'expiring_soon']

    def get_is_low(self, obj):
        # Fix 1: compare the medicine's TOTAL valid stock, not one batch.
        return obj.total_quantity < obj.reorder_level

    def get_is_expired(self, obj):
        # Fix 2: a separate flag for stock that has already expired.
        return obj.expiry_date < date.today()

    def get_expiring_soon(self, obj):
        # Fix 2: only stock that is NOT expired yet and expires within 30 days.
        days_left = (obj.expiry_date - date.today()).days
        return 0 <= days_left <= 30