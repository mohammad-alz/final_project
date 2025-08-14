from django.urls import path, include
from rest_framework import permissions
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, FAQViewSet, LicenseViewSet, PriceViewSet, GoldTradeViewSet,
    RialWalletViewSet, GoldTransactionHistoryViewSet, RialTransactionHistoryViewSet, 
    LogoutView, PaymentWebhookView, PriceChartView, CustomAPIRootView
)

class PublicAPIRootRouter(DefaultRouter):
    """
    A custom router that makes the API Root view public and uses our custom view class.
    """
    # Tell the router to use our custom view for the root page
    APIRootView = CustomAPIRootView

    def get_api_root_view(self, api_urls=None):
        # This part that makes the page public is still needed
        root_view = super().get_api_root_view(api_urls=api_urls)
        root_view.cls.permission_classes = [permissions.AllowAny]
        return root_view

router = PublicAPIRootRouter()
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
]