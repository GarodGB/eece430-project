from rest_framework import serializers
from .models import Medicine
from .models import Medicine, Stock
from datetime import date


class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = ['id', 'name', 'generic_name', 'barcode', 'price', 'needs_prescription']
        
        
        
class StockSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    is_low = serializers.SerializerMethodField()
    expiring_soon = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = ['id', 'medicine', 'medicine_name', 'quantity', 'reorder_level',
                  'expiry_date', 'is_low', 'expiring_soon']

    def get_is_low(self, obj):
        return obj.quantity < obj.reorder_level

    def get_expiring_soon(self, obj):
        return (obj.expiry_date - date.today()).days <= 30