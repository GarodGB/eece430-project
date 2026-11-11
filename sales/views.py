from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from django.db import transaction
from rest_framework import status, serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from inventory.models import Medicine, Stock
from .models import Sale, SaleItem
from .serializers import SaleCreateSerializer, SaleSerializer


@api_view(['POST'])
def create_sale(request):
    user = request.user

    if not user.pharmacy:
        return Response({'error': 'You must belong to a pharmacy to sell.'},
                        status=status.HTTP_400_BAD_REQUEST)

    input_data = SaleCreateSerializer(data=request.data)
    input_data.is_valid(raise_exception=True)
    data = input_data.validated_data

    with transaction.atomic():
        sale = Sale.objects.create(
            pharmacy=user.pharmacy,
            sold_by=user,
            payment_method=data['payment_method'],
        )
        subtotal = Decimal('0')
        cost_total = Decimal('0')

        for item in data['items']:
            try:
                medicine = Medicine.objects.get(barcode=item['barcode'])
            except Medicine.DoesNotExist:
                raise serializers.ValidationError(
                    f"No medicine with barcode {item['barcode']}.")

            # Fix 3: select_for_update() locks these rows until the sale finishes,
            # so two sales at the same moment can't both take the last boxes.
            stocks = list(
                Stock.objects.select_for_update().filter(
                    pharmacy=user.pharmacy,
                    medicine=medicine,
                    quantity__gt=0,
                    expiry_date__gte=date.today(),
                ).order_by('expiry_date')
            )

            available = sum(s.quantity for s in stocks)
            if available < item['quantity']:
                raise serializers.ValidationError(
                    f"Not enough {medicine.name} ({available} left).")

            remaining = item['quantity']
            for s in stocks:
                take = min(s.quantity, remaining)
                s.quantity -= take
                s.save()
                remaining -= take
                if remaining == 0:
                    break

            SaleItem.objects.create(
                sale=sale,
                medicine=medicine,
                quantity=item['quantity'],
                unit_price=medicine.price,
                unit_cost=medicine.cost,
            )
            subtotal += medicine.price * item['quantity']
            cost_total += medicine.cost * item['quantity']

        # Discount on the whole receipt.
        discount = data['discount_percent']
        total = (subtotal * (100 - discount) / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # A discount must never make the customer pay below cost.
        if discount > 0 and total < cost_total:
            max_discount = ((subtotal - cost_total) / subtotal * 100).quantize(
                Decimal('0.01'), rounding=ROUND_DOWN)
            if max_discount <= 0:
                raise serializers.ValidationError(
                    "No discount is possible on this sale: it is already at cost.")
            raise serializers.ValidationError(
                f"This discount would sell below cost. "
                f"Maximum discount for this sale: {max_discount}%.")

        sale.subtotal = subtotal
        sale.discount_percent = discount
        sale.total = total
        sale.save()

    return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)