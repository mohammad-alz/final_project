from django.urls import path, include
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, FAQViewSet, LicenseViewSet, GoldTradeViewSet,
    RialWalletViewSet, GoldTransactionHistoryViewSet, RialTransactionHistoryViewSet, 
    LogoutView, PaymentWebhookView, PriceChartView,MyTokenObtainPairView,
    LatestPriceView, UserBankAccountViewSet, AdminBankAccountViewSet,
    TicketViewSet, AdminVerificationViewSet, UserVerificationView,
    AdminLicenseViewSet, TechnicalAnalysisView, SignalPredictionView,
    AdminUserViewSet, AdminGoldTransactionViewSet, AdminTicketViewSet,
    AdminFAQViewSet, ReportingDashboardView, AdminRialTransactionViewSet,
)

router = DefaultRouter()

router.register(r'users', UserViewSet, basename='user')
router.register(r'faqs', FAQViewSet, basename='faq')
router.register(r'licenses', LicenseViewSet, basename='license')
router.register(r'trade/gold', GoldTradeViewSet, basename='gold-trade')
router.register(r'wallet/rial', RialWalletViewSet, basename='rial-wallet')
router.register(r'history/gold', GoldTransactionHistoryViewSet, basename='gold-history')
router.register(r'history/rial', RialTransactionHistoryViewSet, basename='rial-history')
router.register(r'my-bank-accounts', UserBankAccountViewSet, basename='my-bank-account')
router.register(r'admin/bank-accounts', AdminBankAccountViewSet, basename='admin-bank-account')
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'admin/verifications', AdminVerificationViewSet, basename='admin-verification')
router.register(r'admin/licenses', AdminLicenseViewSet, basename='admin-license')
router.register(r'admin/users', AdminUserViewSet, basename='admin-user')
router.register(r'admin/gold-transactions', AdminGoldTransactionViewSet, basename='admin-gold-transaction')
router.register(r'admin/tickets', AdminTicketViewSet, basename='admin-ticket')
router.register(r'admin/faqs', AdminFAQViewSet, basename='admin-faq')
router.register(r'admin/rial-transactions', AdminRialTransactionViewSet, basename='admin-rial-transaction')

urlpatterns = [
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('payments/webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
    path('prices/latest/', LatestPriceView.as_view(), name='latest-price'),
    path('prices/chart/', PriceChartView.as_view(), name='price-chart'),
    path('prices/analysis/', TechnicalAnalysisView.as_view(), name='price-analysis'),
    path('auth/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verification/status', UserVerificationView.as_view(), name='verification-status'),
    path('prices/predict-signal/', SignalPredictionView.as_view(), name='price-predict-signal'),
    path('admin/reports/dashboard/', ReportingDashboardView.as_view(), name='admin-report-dashboard'),
    path('', include(router.urls)),
]