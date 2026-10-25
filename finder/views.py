from datetime import date
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from inventory.models import Medicine, Stock
from .serializers import PharmacyPublicSerializer


@api_view(['GET'])
def nearby_availability(request):
    q = request.query_params.get('q', '').strip()
    if not q:
        return Response({'error': 'Add ?q= with a medicine name or barcode.'},
                        status=status.HTTP_400_BAD_REQUEST)

    medicines = Medicine.objects.filter(
        Q(name__icontains=q) | Q(generic_name__icontains=q) | Q(barcode=q)
    )

    stocks = Stock.objects.filter(
        medicine__in=medicines,
        quantity__gt=0,
        expiry_date__gte=date.today(),
        pharmacy__shares_stock=True,
    ).exclude(pharmacy=request.user.pharmacy)

    results = {}
    for s in stocks:
        key = (s.pharmacy_id, s.medicine_id)
        results[key] = {
            'pharmacy': PharmacyPublicSerializer(s.pharmacy).data,
            'medicine': s.medicine.name,
            'available': True,
        }

    return Response(list(results.values()))
