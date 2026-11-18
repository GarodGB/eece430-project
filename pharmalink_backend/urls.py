from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from prediction.views import low_stock_alerts, reorder_suppliers, purchase_orders, update_purchase_order_status

from accounts.views import me, pharmacy_sharing
from finder.views import nearby_availability
from inventory.views import MedicineSearchView, MyStockView
from reports.views import weekly_report
from sales.views import create_sale

urlpatterns = [
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
    path('api/sales/', create_sale),
    path('api/finder/', nearby_availability),
    path('api/reports/weekly/', weekly_report),
]