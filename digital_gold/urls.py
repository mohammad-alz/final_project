from django.contrib import admin
from django.urls import path, include
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import permissions
from django.conf import settings
from django.conf.urls.static import static

class CustomAPIRootView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        data = {
            "users": reverse("api:user-list", request=request),
            "faqs": reverse("api:faq-list", request=request),
            "licenses": reverse("api:license-list", request=request),
            "trade-gold": reverse("api:gold-trade-list", request=request),
            "wallet-rial": reverse("api:rial-wallet-list", request=request),
            "history-gold": reverse("api:gold-history-list", request=request),
            "history-rial": reverse("api:rial-history-list", request=request),
            "token-obtain-pair": reverse("api:token_obtain_pair", request=request),
            "token-refresh": reverse("api:token_refresh", request=request),
            "logout": reverse("api:auth_logout", request=request),
            "price-chart": reverse("api:price-chart", request=request),
            "latest-price": reverse("api:latest-price", request=request),
            "my-bank-account": reverse("api:my-bank-account-list", request=request),
            "admin-bank-account": reverse("api:admin-bank-account-list", request=request),
            "ticket": reverse("api:ticket-list", request=request),
        }
        return Response(dict(sorted(data.items())))

urlpatterns = [
    path('admin/', admin.site.urls),
    # Main API entry point
    path('api/', CustomAPIRootView.as_view(), name='api-root'),
    path('api/', include(('api.urls', 'api'), namespace='api')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)