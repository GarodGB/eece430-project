from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from prediction.views import (
    low_stock_alerts, purchase_orders, reorder_suppliers, stock_forecasts,
    update_purchase_order_status,
)

from accounts.views import me, pharmacy_sharing
from finder.views import nearby_availability
from insurance.views import daman_overview, daman_statement_detail, daman_statements, mark_statement_paid
from inventory.views import MedicineSearchView, MyStockView
from inventory.reservation_api import reservations, release_reservation
from reports.views import weekly_report
from sales.views import create_sale

urlpatterns = [
    path('api/prediction/forecasts/', stock_forecasts),
    path('api/alerts/low-stock/', low_stock_alerts),
    path('api/reorder/suppliers/', reorder_suppliers),
    path('api/reorder/orders/', purchase_orders),
    path('api/reorder/orders/<int:order_id>/', update_purchase_order_status),
    path('admin/', admin.site.urls),
    
    path('api/login/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/me/', me),
    path('api/pharmacy/sharing/', pharmacy_sharing),
    path('api/medicines/', MedicineSearchView.as_view()),
    path('api/stock/', MyStockView.as_view()),
    path('api/reservations/', reservations),
    path('api/reservations/<int:reservation_id>/release/', release_reservation),
    path('api/sales/', create_sale),
    path('api/finder/', nearby_availability),
    path('api/reports/weekly/', weekly_report),
    path('api/insurance/daman/', daman_overview),
    path('api/insurance/daman/statements/', daman_statements),
    path('api/insurance/daman/statements/<int:statement_id>/', daman_statement_detail),
    path('api/insurance/daman/statements/<int:statement_id>/mark-paid/', mark_statement_paid),
]
