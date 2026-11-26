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
    # The pharmacist ticks this after checking the customer's prescription.
    # Needed only when the cart has a medicine that needs a prescription.
    prescription_confirmed = serializers.BooleanField(default=False)
    # PHAR-16: needed only when the payment is "insurance" (Daman).
    daman_number = serializers.RegexField(
        r'^\d{1,20}$', required=False, allow_blank=True,
        error_messages={'invalid': 'The Daman number can only contain digits.'},
    )
    items = SaleItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("A sale needs at least one item.")
        return value

    def validate(self, data):
        if data.get('payment_method') == 'insurance' and not data.get('daman_number'):
            raise serializers.ValidationError({'daman_number': "Enter the patient's Daman number for a Daman sale."})
        return data


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
    daman = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ['id', 'pharmacy', 'sold_by', 'created_at', 'payment_method',
                  'subtotal', 'discount_percent', 'total', 'daman', 'items']

    def get_daman(self, sale):
        # PHAR-16: for a Daman sale, who pays what. Empty for cash and card sales.
        claim = getattr(sale, 'claim', None)
        if claim is None:
            return None
        return {
            'daman_number': claim.policy_number,
            'daman_pays': str(Decimal(claim.amount).quantize(Decimal('0.01'))),
            'customer_pays': str(Decimal(claim.customer_paid).quantize(Decimal('0.01'))),
        }
