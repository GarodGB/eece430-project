from datetime import date

from django.db.models import IntegerField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from rest_framework import filters, generics

from .models import Medicine, Stock
from .serializers import MedicineSerializer, StockSerializer


class MedicineSearchView(generics.ListAPIView):
    queryset = Medicine.objects.all().order_by('name')
    serializer_class = MedicineSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'generic_name', 'barcode']


class MyStockView(generics.ListAPIView):
    serializer_class = StockSerializer

    def get_queryset(self):
        user = self.request.user

        # Total valid (not expired) quantity of the same medicine in the same pharmacy,
        # calculated by the database for every row in one query.
        total_valid = (
            Stock.objects
            .filter(
                pharmacy=OuterRef('pharmacy'),
                medicine=OuterRef('medicine'),
                expiry_date__gte=date.today(),
            )
            .values('pharmacy', 'medicine')
            .annotate(total=Sum('quantity'))
            .values('total')
        )

        stocks = Stock.objects.select_related('medicine').annotate(
            total_quantity=Coalesce(Subquery(total_valid, output_field=IntegerField()), 0)
        ).order_by('expiry_date')

        if user.is_superuser:
            return stocks
        return stocks.filter(pharmacy=user.pharmacy)