from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from accounts.views import me   
from inventory.views import MedicineSearchView 
from inventory.views import MedicineSearchView, MyStockView 
from sales.views import create_sale
from finder.views import nearby_availability 
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/login/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/me/', me),
    path('api/medicines/', MedicineSearchView.as_view()), 
    path('api/stock/', MyStockView.as_view()), 
    path('api/sales/', create_sale),
    path('api/finder/', nearby_availability),  
        
]
