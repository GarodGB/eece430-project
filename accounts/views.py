from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .permissions import IsPharmacyOwner
from .serializers import UserSerializer


@api_view(['GET'])
def me(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET', 'PATCH'])
@permission_classes([IsPharmacyOwner])
def pharmacy_sharing(request):
    pharmacy = request.user.pharmacy

    if request.method == 'PATCH':
        value = request.data.get('shares_stock')
        if not isinstance(value, bool):
            return Response({'error': 'shares_stock must be true or false.'},
                            status=status.HTTP_400_BAD_REQUEST)
        pharmacy.shares_stock = value
        pharmacy.save(update_fields=['shares_stock'])

    return Response({'pharmacy': pharmacy.name, 'shares_stock': pharmacy.shares_stock})