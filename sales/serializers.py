from decimal import Decimal

from rest_framework import serializers

from .models import Sale, SaleItem


# ---------- What React SENDS (input) ----------

class SaleItemInputSerializer(serializers.Serializer):
    barcode = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)


class SaleCreateSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=Sale.PAYMENT_CHOICES, default='cash')
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2,
        min_value=Decimal('0'), max_value=Decimal('100'),
        default=Decimal('0'),
    )
    items = SaleItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("A sale needs at least one item.")
        return value


# ---------- What the server SENDS BACK (the receipt) ----------
# unit_cost is NOT sent back: the buying price stays private.

class SaleItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)

    class Meta:
        model = SaleItem
        fields = ['medicine', 'medicine_name', 'quantity', 'unit_price']


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    sold_by = serializers.CharField(source='sold_by.username', read_only=True)

    class Meta:
        model = Sale
        fields = ['id', 'pharmacy', 'sold_by', 'created_at', 'payment_method',
                  'subtotal', 'discount_percent', 'total', 'items']
