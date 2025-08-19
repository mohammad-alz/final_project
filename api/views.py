import hashlib
import hmac
from decimal import Decimal
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework import viewsets, permissions, status, mixins,generics
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.decorators import action
from rest_framework.routers import APIRootView
from rest_framework.reverse import reverse
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import (
    User, GoldTransaction, RialTransaction, Price, FAQ, License, GoldWallet, RialWallet, BankAccount
)
from .serializers import (
    UserSerializer, GoldTransactionSerializer, RialTransactionSerializer,
    PriceSerializer, FAQSerializer, LicenseSerializer,GoldTradeSerializer,
    MyTokenObtainPairSerializer, BankAccountSerializer, EmptySerializer
)

# --- User and Public Views ---

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        return User.objects.filter(pk=self.request.user.pk) if self.request.user.is_authenticated else User.objects.none()

    def get_object(self):
        return self.request.user

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        try:
            send_mail('Welcome!', f'Hello {user.first_name},\n\nThank you for registering.', settings.DEFAULT_FROM_EMAIL, [user.email])
        except Exception as e:
            print(f"Failed to send welcome email: {e}")
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQ.objects.filter(is_active=True).order_by('sort_order')
    serializer_class = FAQSerializer
    permission_classes = [permissions.AllowAny]

class LicenseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = License.objects.filter(status='ACTIVE')
    serializer_class = LicenseSerializer
    permission_classes = [permissions.AllowAny]

class LatestPriceView(generics.GenericAPIView):
    """
    An endpoint that returns only the single, most recent price object.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PriceSerializer # Reuse the existing PriceSerializer

    def get(self, request, *args, **kwargs):
        try:
            # This is a very efficient way to get the latest record
            latest_price = Price.objects.latest('timestamp')
            serializer = self.get_serializer(latest_price)
            return Response(serializer.data)
        except Price.DoesNotExist:
            return Response({"error": "No price data available."}, status=status.HTTP_404_NOT_FOUND)


# --- Trading and Wallet Logic ---

class GoldTradeViewSet(mixins.ListModelMixin,viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    # Connect the new serializer to the view
    serializer_class = GoldTradeSerializer
    queryset = GoldTransaction.objects.none()
    
    def _trade(self, request, trade_type):
        user = request.user

        # --- THIS IS THE NEW VALIDATION LOGIC ---
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity_in_milligrams = serializer.validated_data['quantity']
        # ----------------------------------------
        
        # The rest of the logic is the same as before
        try:
            price_per_gram = Price.objects.latest('timestamp').price
        except Price.DoesNotExist:
            return Response({'error': 'Pricing unavailable.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        exact_value = (Decimal(quantity_in_milligrams) / Decimal(1000)) * Decimal(price_per_gram)
        final_rial_value = int(round(exact_value))

        with transaction.atomic():
            # ... (the rest of the transaction logic is unchanged) ...
            gold_wallet = GoldWallet.objects.select_for_update().get(user=user)
            rial_wallet = RialWallet.objects.select_for_update().get(user=user)

            if trade_type == 'BUY':
                if rial_wallet.balance < final_rial_value: return Response({'error': 'Insufficient funds'}, status=status.HTTP_400_BAD_REQUEST)
                rial_wallet.balance -= final_rial_value
                gold_wallet.balance += quantity_in_milligrams
            else:
                if gold_wallet.balance < quantity_in_milligrams: return Response({'error': 'Insufficient gold'}, status=status.HTTP_400_BAD_REQUEST)
                gold_wallet.balance -= quantity_in_milligrams
                rial_wallet.balance += final_rial_value

            rial_wallet.save()
            gold_wallet.save()
            tx = GoldTransaction.objects.create(user=user, transaction_type=trade_type, quantity=quantity_in_milligrams, price_per_unit=price_per_gram, total_price=final_rial_value, net_amount=final_rial_value, status='COMPLETED')
        return Response(GoldTransactionSerializer(tx).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def buy(self, request):
        return self._trade(request, 'BUY')

    @action(detail=False, methods=['post'])
    def sell(self, request):
        return self._trade(request, 'SELL')

class RialWalletViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RialTransactionSerializer
    queryset = RialTransaction.objects.none()
    @action(detail=False, methods=['post'])
    def deposit(self, request):
        try:
            amount = int(request.data.get('amount'))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        tx = RialTransaction.objects.create(user=request.user, transaction_type='DEPOSIT', amount=amount, status='PENDING')
        return Response({'message': 'Deposit request received', 'transaction': RialTransactionSerializer(tx).data}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'])
    def withdraw(self, request):
        try:
            amount = int(request.data.get('amount'))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            rial_wallet = RialWallet.objects.select_for_update().get(user=request.user)
            if rial_wallet.balance < amount:
                return Response({'error': 'Insufficient funds'}, status=status.HTTP_400_BAD_REQUEST)
            rial_wallet.balance -= amount
            rial_wallet.save()
            tx = RialTransaction.objects.create(user=request.user, transaction_type='WITHDRAWAL', amount=amount, status='PENDING')
        return Response({'message': 'Withdrawal request received', 'transaction': RialTransactionSerializer(tx).data}, status=status.HTTP_202_ACCEPTED)


# --- Transaction History ---

class TransactionHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        model = self.serializer_class.Meta.model
        return model.objects.filter(user=user).order_by('-timestamp')

class GoldTransactionHistoryViewSet(TransactionHistoryViewSet):
    serializer_class = GoldTransactionSerializer

class RialTransactionHistoryViewSet(TransactionHistoryViewSet):
    serializer_class = RialTransactionSerializer


# --- Authentication and Webhooks ---

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@method_decorator(csrf_exempt, name='dispatch')
class PaymentWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        received_signature = request.headers.get('X-Payment-Signature')
        webhook_secret = getattr(settings, 'PAYMENT_WEBHOOK_SECRET', None)
        if not webhook_secret:
            return Response({'error': 'Webhook secret not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        expected_signature = hmac.new(key=webhook_secret.encode(), msg=request.body, digestmod=hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_signature, received_signature or ''):
            return Response({'error': 'Invalid signature'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        try:
            with transaction.atomic():
                rial_tx = RialTransaction.objects.select_for_update().get(id=data.get('transaction_id'), status='PENDING')
                if data.get('status') == 'completed':
                    rial_tx.status = 'COMPLETED'
                    rial_tx.notes = 'Payment confirmed via webhook.'
                    wallet = RialWallet.objects.select_for_update().get(user=rial_tx.user)
                    wallet.balance += rial_tx.amount
                    wallet.save()
                    try:
                        send_mail('Deposit Successful!', f'Your deposit of {rial_tx.amount} has been processed.', settings.DEFAULT_FROM_EMAIL, [rial_tx.user.email])
                    except Exception as e:
                        print(f"Failed to send deposit confirmation email: {e}")
                else:
                    rial_tx.status = 'FAILED'
                    rial_tx.notes = 'Payment failed via webhook.'
                rial_tx.save()
            return Response({'status': 'success'})
        except RialTransaction.DoesNotExist:
            return Response({'error': 'Transaction not found or already processed'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Internal error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class PriceChartView(APIView):
    """
    Provides evenly sampled data for a simple chart.
    Accepts:
    - timeframe: 'daily', 'weekly', 'monthly' (default: 'daily')
    - points: The number of data points to return (default: 100)
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        # 1. Get parameters from the URL
        timeframe = request.query_params.get('timeframe', 'daily')
        try:
            points_count = int(request.query_params.get('points', '100'))
        except (ValueError, TypeError):
            points_count = 100

        # 2. Determine the date range
        end_date = timezone.now()
        if timeframe == 'weekly':
            start_date = end_date - timedelta(days=7)
        elif timeframe == 'monthly':
            start_date = end_date - timedelta(days=30)
        else: # 'daily'
            start_date = end_date - timedelta(days=1)
        
        # 3. Fetch all relevant data points from the database
        queryset = Price.objects.filter(
            timestamp__gte=start_date
        ).order_by('timestamp')
        
        # 4. Sample the data to get the desired number of points
        total_points_in_db = queryset.count()
        if total_points_in_db > points_count:
            # Calculate the step to slice the queryset
            step = total_points_in_db // points_count
            if step == 0:
                 step = 1 # prevent step from being zero
            sampled_queryset = queryset[::step]
        else:
            # If we have fewer points in the DB than requested, return all of them
            sampled_queryset = queryset

        # 5. Serialize and return the sampled data
        serializer = PriceSerializer(sampled_queryset, many=True)
        return Response(serializer.data)
    
class CustomAuthToken(ObtainAuthToken):
    renderer_classes = [BrowsableAPIRenderer, JSONRenderer]

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class UserBankAccountViewSet(viewsets.ModelViewSet):
    """
    Allows users to add, view, and delete their own bank accounts.
    """
    serializer_class = BankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # A user can only ever see their own bank accounts.
        return BankAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # When creating a new bank account, automatically assign it to the logged-in user.
        serializer.save(user=self.request.user)

# --- View for ADMINS to manage all accounts ---
class AdminBankAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Allows admins to view all bank accounts and verify them.
    """
    serializer_class = BankAccountSerializer
    permission_classes = [permissions.IsAdminUser] # Only admins can access
    queryset = BankAccount.objects.all()

    def get_serializer_class(self):
        if self.action in ['verify', 'reject']:
            return EmptySerializer
        return super().get_serializer_class()


    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """An action to mark an account as verified."""
        account = self.get_object()
        account.status = BankAccount.VerificationStatus.VERIFIED
        account.save()
        return Response({'status': 'Account verified'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """An action to mark an account as rejected."""
        account = self.get_object()
        account.status = BankAccount.VerificationStatus.REJECTED
        account.save()
        return Response({'status': 'Account rejected'})