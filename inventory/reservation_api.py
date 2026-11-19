
from datetime import date

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.models import Pharmacy
from accounts.permissions import IsPharmacyStaff
from inventory.models import Medicine, MedicineReservation, Stock


class ReservationInput(serializers.Serializer):
    medicine_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=1000000)
    customer_name = serializers.CharField(max_length=120, trim_whitespace=True)
    customer_phone = serializers.RegexField(
        regex=r'^\+?[\d ()-]{5,25}$',
        required=False,
        allow_blank=True,
        error_messages={
            'invalid': 'Enter a valid contact number or leave it blank.'
        },
    )
    request_key = serializers.UUIDField(required=False)


class ReservationOutput(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source='medicine.name',
        read_only=True
    )
    medicine_barcode = serializers.CharField(
        source='medicine.barcode',
        read_only=True
    )
    reserved_by = serializers.CharField(
        source='reserved_by.username',
        read_only=True,
        default=''
    )
    released_by = serializers.CharField(
        source='released_by.username',
        read_only=True,
        default=''
    )

    class Meta:
        model = MedicineReservation
        fields = (
            'id',
            'medicine',
            'medicine_name',
            'medicine_barcode',
            'customer_name',
            'customer_phone',
            'quantity',
            'status',
            'reserved_by',
            'created_at',
            'released_by',
            'released_at',
        )


@api_view(['GET', 'POST'])
@permission_classes([IsPharmacyStaff])
def reservations(request):
    """Create/list reservations for the current user's pharmacy only."""

    user = request.user

    if request.method == 'GET':
        qs = (
            MedicineReservation.objects
            .filter(pharmacy_id=user.pharmacy_id)
            .select_related(
                'medicine',
                'reserved_by',
                'released_by'
            )
            .order_by('-created_at', '-id')
        )

        return Response(
            ReservationOutput(qs[:500], many=True).data
        )

    payload = ReservationInput(data=request.data)
    payload.is_valid(raise_exception=True)
    data = payload.validated_data

    with transaction.atomic():

        # Lock the pharmacy to prevent simultaneous
        # reservations and checkouts from overbooking stock.
        Pharmacy.objects.select_for_update().get(
            pk=user.pharmacy_id
        )

        key = data.get('request_key')

        if key:
            prior = (
                MedicineReservation.objects
                .filter(
                    pharmacy_id=user.pharmacy_id,
                    request_key=key
                )
                .select_related(
                    'medicine',
                    'reserved_by',
                    'released_by'
                )
                .first()
            )

            if prior:
                if (
                    prior.medicine_id != data['medicine_id']
                    or prior.quantity != data['quantity']
                    or prior.customer_name != data['customer_name']
                    or prior.customer_phone != data.get('customer_phone', '')
                ):
                    return Response(
                        {
                            'error': (
                                'This request key was already used '
                                'for another reservation.'
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                return Response(
                    ReservationOutput(prior).data,
                    status=status.HTTP_200_OK
                )

        medicine = Medicine.objects.filter(
            pk=data['medicine_id']
        ).first()

        if not medicine:
            raise serializers.ValidationError(
                {'medicine_id': 'Medicine not found.'}
            )

        physical = (
            Stock.objects.filter(
                pharmacy_id=user.pharmacy_id,
                medicine=medicine,
                expiry_date__gte=date.today()
            )
            .aggregate(total=Sum('quantity'))['total'] or 0
        )

        held = (
            MedicineReservation.objects.filter(
                pharmacy_id=user.pharmacy_id,
                medicine=medicine,
                status=MedicineReservation.ACTIVE
            )
            .aggregate(total=Sum('quantity'))['total'] or 0
        )

        available = max(0, physical - held)

        if data['quantity'] > available:
            raise serializers.ValidationError({
                'quantity': (
                    f'Only {available} unreserved, '
                    f'unexpired unit(s) available.'
                )
            })

        reservation = MedicineReservation.objects.create(
            pharmacy_id=user.pharmacy_id,
            medicine=medicine,
            customer_name=data['customer_name'],
            customer_phone=data.get('customer_phone', ''),
            quantity=data['quantity'],
            reserved_by=user,
            request_key=key,
        )

    return Response(
        ReservationOutput(reservation).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([IsPharmacyStaff])
def release_reservation(request, reservation_id):
    """Only an explicit release frees the reserved quantity."""

    with transaction.atomic():

        Pharmacy.objects.select_for_update().get(
            pk=request.user.pharmacy_id
        )

        # Lock the reservation without joining nullable
        # user fields, which PostgreSQL does not allow
        # with SELECT FOR UPDATE.
        reservation = (
            MedicineReservation.objects
            .select_for_update()
            .filter(
                pk=reservation_id,
                pharmacy_id=request.user.pharmacy_id,
            )
            .first()
        )

        if reservation is None:
            return Response(
                {'detail': 'Reservation not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if reservation.status == MedicineReservation.ACTIVE:
            reservation.status = MedicineReservation.RELEASED
            reservation.released_at = timezone.now()
            reservation.released_by = request.user

            reservation.save(
                update_fields=[
                    'status',
                    'released_at',
                    'released_by'
                ]
            )

    return Response(
        ReservationOutput(reservation).data
    )
