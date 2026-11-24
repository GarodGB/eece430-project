"""Stock forecasts, low-stock alerts, and reordering for the signed-in pharmacy."""

from datetime import date, timedelta

from django.utils import timezone

from django.db import transaction
from django.db.models import F, Max, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsPharmacyStaff, IsPharmacyOwner
from accounts.models import Pharmacy
from inventory.models import Stock, MedicineReservation
from prediction.models import DailySales, PurchaseOrder, Supplier


FORECAST_LOOKBACK_DAYS = 30


@api_view(['GET'])
@permission_classes([IsPharmacyStaff])
def stock_forecasts(request):
    today = timezone.localdate()
    start = today - timedelta(days=FORECAST_LOOKBACK_DAYS)
    pharmacy_id = request.user.pharmacy_id

    inventory = (
        Stock.objects.filter(pharmacy_id=pharmacy_id)
        .values('medicine_id', 'medicine__name', 'medicine__generic_name', 'medicine__barcode')
        .annotate(unexpired=Coalesce(Sum('quantity', filter=Q(expiry_date__gte=today)), 0))
        .order_by('medicine__name', 'medicine_id')
    )
    held = {
        row['medicine_id']: row['total']
        for row in MedicineReservation.objects.filter(
            pharmacy_id=pharmacy_id, status=MedicineReservation.ACTIVE,
        ).order_by().values('medicine_id').annotate(total=Sum('quantity'))
    }
    sold = {
        row['medicine_id']: row['total']
        for row in DailySales.objects.filter(
            pharmacy_id=pharmacy_id, date__gte=start, date__lt=today,
        ).values('medicine_id').annotate(total=Sum('quantity_sold'))
    }

    forecasts = []
    for row in inventory:
        medicine_id = row['medicine_id']
        available = max(0, row['unexpired'] - held.get(medicine_id, 0))
        total_sold = sold.get(medicine_id, 0)
        days = None
        run_out_date = None
        if available == 0:
            forecast_status = 'out_of_stock'
            days = 0
            run_out_date = today
        elif total_sold == 0:
            forecast_status = 'no_recent_sales'
        else:
            forecast_status = 'estimated'
            # Round up using the exact rate before formatting it for display.
            days = (available * FORECAST_LOOKBACK_DAYS + total_sold - 1) // total_sold
            if days <= (date.max - today).days:
                run_out_date = today + timedelta(days=days)

        forecasts.append({
            'medicine_id': medicine_id,
            'medicine_name': row['medicine__name'],
            'generic_name': row['medicine__generic_name'],
            'barcode': row['medicine__barcode'],
            'available_quantity': available,
            'total_units_sold': total_sold,
            'average_daily_sales': total_sold / FORECAST_LOOKBACK_DAYS,
            'days_remaining': days,
            'predicted_run_out_date': run_out_date.isoformat() if run_out_date else None,
            'status': forecast_status,
        })

    return Response({
        'as_of_date': today.isoformat(),
        'lookback_days': FORECAST_LOOKBACK_DAYS,
        'forecasts': forecasts,
    })


@api_view(['GET'])
@permission_classes([IsPharmacyStaff])
def low_stock_alerts(request):
    """Return one alert per medicine when total unexpired stock is below threshold.

    This is a read-only, threshold-based alert list, *not* an ML prediction.
    We use the highest reorder level if a pharmacy has multiple batches of
    the same medicine with differing thresholds.
    """
    rows = (
        Stock.objects.filter(pharmacy=request.user.pharmacy)
        .values('medicine_id', 'medicine__name')
        .annotate(
            available_quantity=Coalesce(
                Sum('quantity', filter=Q(expiry_date__gte=date.today())),
                0,
            ),
            reorder_level=Max('reorder_level'),
        )
        .order_by('medicine__name', 'medicine_id')
    )
    held = {
        row['medicine_id']: row['total']
        for row in (MedicineReservation.objects
                    .filter(pharmacy=request.user.pharmacy,
                            status=MedicineReservation.ACTIVE)
                    .values('medicine_id').annotate(total=Sum('quantity')))
    }
    alerts = []
    for row in rows:
        sellable = max(0, row['available_quantity'] - held.get(row['medicine_id'], 0))
        if sellable < row['reorder_level']:
            alerts.append({
                'medicine_id': row['medicine_id'],
                'medicine_name': row['medicine__name'],
                'available_quantity': sellable,
                'reorder_level': row['reorder_level'],
                'shortfall': row['reorder_level'] - sellable,
            })
    return Response(alerts)


class PurchaseOrderRequestSerializer(serializers.Serializer):
    medicine_id = serializers.IntegerField(min_value=1)
    supplier_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=1000000)


class ReceiveDeliverySerializer(serializers.Serializer):
    received_quantity = serializers.IntegerField(min_value=1, max_value=1000000)
    expiry_date = serializers.DateField()

    def validate_expiry_date(self, value):
        if value < date.today():
            raise serializers.ValidationError('Cannot receive an expired medicine batch.')
        return value


def _order_data(order):
    return {
        'id': order.id,
        'pharmacy_id': order.pharmacy_id,
        'medicine_id': order.medicine_id,
        'medicine_name': order.medicine.name,
        'supplier_id': order.supplier_id,
        'supplier_name': order.supplier.name,
        'quantity': order.quantity,
        'status': order.status,
        'created_at': order.created_at.isoformat(),
        'received_quantity': order.received_quantity,
        'received_expiry_date': (order.received_expiry_date.isoformat()
                                 if order.received_expiry_date else None),
        'received_at': order.received_at.isoformat() if order.received_at else None,
        'received_stock_id': order.received_stock_id,
    }


@api_view(['GET'])
@permission_classes([IsPharmacyOwner])
def reorder_suppliers(request):
    """Available suppliers for the owner's reorder form."""
    return Response(list(Supplier.objects.order_by('name', 'id').values(
        'id', 'name', 'phone', 'email'
    )))


@api_view(['GET', 'POST'])
@permission_classes([IsPharmacyOwner])
def purchase_orders(request):
    """Owners view their own orders or create one *pending* reorder.

    The API never sends orders to suppliers and never increases stock.
    A new explicit request may create another pending order for the same medicine.
    """
    pharmacy_id = request.user.pharmacy_id
    if request.method == 'GET':
        orders = (PurchaseOrder.objects.filter(pharmacy_id=pharmacy_id)
                  .select_related('medicine', 'supplier').order_by('-created_at', '-id'))
        return Response([_order_data(order) for order in orders])

    form = PurchaseOrderRequestSerializer(data=request.data)
    form.is_valid(raise_exception=True)
    med_id = form.validated_data['medicine_id']
    supplier_id = form.validated_data['supplier_id']
    quantity = form.validated_data['quantity']

    if not Supplier.objects.filter(pk=supplier_id).exists():
        return Response({'error': 'Supplier not found.'}, status=status.HTTP_400_BAD_REQUEST)

    # Lock the pharmacy record while checking this pharmacy's inventory.
    # Each intentional POST creates a separate pending purchase order.
    with transaction.atomic():
        pharmacy = Pharmacy.objects.select_for_update().get(pk=pharmacy_id)
        stocks = Stock.objects.filter(pharmacy=pharmacy, medicine_id=med_id)
        if not stocks.exists():
            return Response({'error': 'Medicine is not stocked by your pharmacy.'},
                            status=status.HTTP_400_BAD_REQUEST)

        totals = stocks.aggregate(
            available=Coalesce(Sum('quantity', filter=Q(expiry_date__gte=date.today())), 0),
            threshold=Max('reorder_level'),
        )
        held = (MedicineReservation.objects.filter(
            pharmacy=pharmacy, medicine_id=med_id,
            status=MedicineReservation.ACTIVE,
        ).aggregate(total=Sum('quantity'))['total'] or 0)
        if max(0, totals['available'] - held) >= totals['threshold']:
            return Response({'error': 'This medicine is not currently below its reorder level.'},
                            status=status.HTTP_400_BAD_REQUEST)

        order = PurchaseOrder.objects.create(
            pharmacy=pharmacy,
            medicine_id=med_id,
            supplier_id=supplier_id,
            quantity=quantity,
            status='pending',
        )
        order = PurchaseOrder.objects.select_related('medicine', 'supplier').get(pk=order.pk)
        return Response(_order_data(order), status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsPharmacyOwner])
def update_purchase_order_status(request, order_id):
    """Owner advances pending->sent->received. Receipt creates one batch atomically.

    Never contacts suppliers. Received cannot be reversed; old received orders
    from before this update are NOT backfilled, to avoid double-counting stock.
    """
    desired = request.data.get('status')
    if desired not in ('sent', 'received'):
        return Response({'error': 'Status must be sent or received.'},
                        status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        # Lock the order in PostgreSQL so two simultaneous receipt requests
        # cannot both add new stock.
        order = (PurchaseOrder.objects.select_for_update()
                 .select_related('medicine', 'supplier')
                 .filter(pk=order_id, pharmacy_id=request.user.pharmacy_id).first())
        if order is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if order.status == desired:
            # Idempotent retry: an already received order NEVER adds stock again.
            if desired == 'received' and order.received_stock_id is not None:
                supplied = request.data.get('received_quantity')
                expiry = request.data.get('expiry_date')
                if ((supplied is not None and str(supplied) != str(order.received_quantity))
                        or (expiry is not None and str(expiry) != str(order.received_expiry_date))):
                    return Response({'error': 'This delivery was already recorded with different details.'},
                                    status=status.HTTP_409_CONFLICT)
            return Response(_order_data(order))

        transitions = {'pending': 'sent', 'sent': 'received'}
        if transitions.get(order.status) != desired:
            return Response({'error': f'Cannot change an order from {order.status} to {desired}.'},
                            status=status.HTTP_409_CONFLICT)

        if desired == 'received':
            receipt = ReceiveDeliverySerializer(data=request.data)
            receipt.is_valid(raise_exception=True)
            quantity = receipt.validated_data['received_quantity']
            expiry_date = receipt.validated_data['expiry_date']
            # Respect the pharmacy's existing medicine reorder threshold.
            threshold = (Stock.objects.filter(pharmacy_id=order.pharmacy_id, medicine_id=order.medicine_id)
                         .aggregate(level=Max('reorder_level'))['level'] or 10)
            stock_batch = Stock.objects.create(
                pharmacy_id=order.pharmacy_id,
                medicine_id=order.medicine_id,
                quantity=quantity,
                reorder_level=threshold,
                expiry_date=expiry_date,
            )
            order.received_quantity = quantity
            order.received_expiry_date = expiry_date
            order.received_at = timezone.now()
            order.received_stock = stock_batch
            order.status = 'received'
            order.save(update_fields=[
                'status', 'received_quantity', 'received_expiry_date',
                'received_at', 'received_stock',
            ])
        else:
            order.status = 'sent'
            order.save(update_fields=['status'])

        return Response(_order_data(order))
