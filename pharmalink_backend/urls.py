from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from accounts.views import me   
from inventory.views import MedicineSearchView 
from inventory.views import MedicineSearchView, MyStockView 
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/login/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/me/', me),
    path('api/medicines/', MedicineSearchView.as_view()), 
    path('api/stock/', MyStockView.as_view()),    
]