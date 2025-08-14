from django.contrib import admin
from django.urls import path, include
from api.views import CustomAuthToken 
from api.views import MyTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Main API entry point
    path('api/', include('api.urls')),
    # Use this endpoint to log in and get your token
    path('api/auth/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]