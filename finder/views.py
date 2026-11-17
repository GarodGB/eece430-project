from datetime import date
from math import asin, cos, radians, sin, sqrt

from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from inventory.models import Medicine, Stock
from .serializers import PharmacyPublicSerializer


def distance_km(lat1, lon1, lat2, lon2):
    """PHAR-10: straight-line distance between two map points (Haversine formula)."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return round(2 * 6371 * asin(sqrt(a)), 1)  # 6371 km = Earth's radius


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
    ).exclude(pharmacy=request.user.pharmacy).select_related('pharmacy', 'medicine')

    # The searching user's own pharmacy is the starting point for distances.
    me = request.user.pharmacy
    my_lat = me.latitude if me else None
    my_lon = me.longitude if me else None

    results = {}
    for s in stocks:
        key = (s.pharmacy_id, s.medicine_id)
        results[key] = {
            'pharmacy': PharmacyPublicSerializer(s.pharmacy).data,
            'medicine': s.medicine.name,
            'available': True,
            'distance_km': distance_km(my_lat, my_lon, s.pharmacy.latitude, s.pharmacy.longitude),
        }

    # Nearest first; pharmacies without a location go last.
    ordered = sorted(
        results.values(),
        key=lambda r: (r['distance_km'] is None, r['distance_km'] or 0, r['pharmacy']['name']),
    )
    return Response(ordered)
