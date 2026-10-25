from rest_framework import generics, filters
from .models import Medicine
from .serializers import MedicineSerializer


class MedicineSearchView(generics.ListAPIView):
    queryset = Medicine.objects.all().order_by('name')
    serializer_class = MedicineSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'generic_name', 'barcode']