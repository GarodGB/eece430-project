from rest_framework import generics, filters
from .models import Medicine
from .serializers import MedicineSerializer
from .models import Stock
from .serializers import StockSerializer


class MedicineSearchView(generics.ListAPIView):
    queryset = Medicine.objects.all().order_by('name')
    serializer_class = MedicineSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'generic_name', 'barcode']
    
    
    



class MyStockView(generics.ListAPIView):
    serializer_class = StockSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Stock.objects.all().order_by('expiry_date')
        return Stock.objects.filter(pharmacy=user.pharmacy).order_by('expiry_date')