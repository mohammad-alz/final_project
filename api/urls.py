from django.urls import path, include
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, FAQViewSet, LicenseViewSet, PriceViewSet, GoldTradeViewSet,
    RialWalletViewSet, GoldTransactionHistoryViewSet, RialTransactionHistoryViewSet, 
    LogoutView, PaymentWebhookView, PriceChartView,MyTokenObtainPairView
)

router = DefaultRouter()

router.register(r'users', UserViewSet, basename='user')
router.register(r'faqs', FAQViewSet, basename='faq')
router.register(r'licenses', LicenseViewSet, basename='license')
router.register(r'prices', PriceViewSet, basename='price')
router.register(r'trade/gold', GoldTradeViewSet, basename='gold-trade')
router.register(r'wallet/rial', RialWalletViewSet, basename='rial-wallet')
router.register(r'history/gold', GoldTransactionHistoryViewSet, basename='gold-history')
router.register(r'history/rial', RialTransactionHistoryViewSet, basename='rial-history')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('payments/webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
    path('prices/chart/', PriceChartView.as_view(), name='price-chart'),
    path('auth/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]