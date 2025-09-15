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
from django.conf import settings
from django.db.models import Sum
from rest_framework import viewsets, permissions, status, mixins,generics
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.decorators import action
from rest_framework.routers import APIRootView
from rest_framework.reverse import reverse
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import (
    User, GoldTransaction, RialTransaction, Price, FAQ, License,
    GoldWallet, RialWallet, BankAccount,Ticket, UserVerification,
    TechnicalAnalysis, PricePrediction,
)
from .serializers import (
    UserSerializer, GoldTransactionSerializer, RialTransactionSerializer,
    PriceSerializer, FAQSerializer, LicenseSerializer,GoldTradeSerializer,
    MyTokenObtainPairSerializer, UserBankAccountSerializer, AdminBankAccountSerializer,
    EmptySerializer, RialTransactionActionSerializer, TicketCreateSerializer,
    TicketDetailSerializer, TicketAnswerSerializer, UserVerificationSerializer,
    AdminVerificationSerializer, UserVerificationSubmitSerializer,
    AdminRejectionSerializer, AdminLicenseSerializer, TechnicalAnalysisSerializer,
    UserCreateSerializer, SignalPredictionSerializer, AdminUserSerializer,
    AdminGoldTransactionSerializer, AdminTicketSerializer, AdminFAQSerializer,
    AdminRialTransactionSerializer,
)

from .filters import (
    GoldTransactionFilter, TicketFilter, RialTransactionFilter,

)

from .permissions import IsVerifiedUser


class UserViewSet(viewsets.ModelViewSet):
    """
    Handles user creation (registration) and profile viewing/updating.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(pk=self.request.user.pk)

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [permissions.AllowAny]
        return super().get_permissions()
        
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def destroy(self, request, *args, **kwargs):
        """
        Disables the DELETE method for this viewset.
        """
        return Response(
            {'detail': 'Account deletion is not allowed.'}, 
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
        

class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQ.objects.filter(is_active=True).order_by('sort_order')
    serializer_class = FAQSerializer
    permission_classes = [permissions.AllowAny]

class LicenseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = License.objects.filter(status='ACTIVE')
    serializer_class = LicenseSerializer
    permission_classes = [permissions.AllowAny]

class AdminLicenseViewSet(viewsets.ModelViewSet):
    """
    An endpoint for admins to create, view, update, and delete licenses.
    """
    serializer_class = AdminLicenseSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = License.all_objects.all()
    parser_classes = [MultiPartParser, FormParser]

class LatestPriceView(generics.GenericAPIView):
    """
    An endpoint that returns only the single, most recent price object.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PriceSerializer

    def get(self, request, *args, **kwargs):
        try:
            latest_price = Price.objects.latest('timestamp')
            serializer = self.get_serializer(latest_price)
            return Response(serializer.data)
        except Price.DoesNotExist:
            return Response({"error": "No price data available."}, status=status.HTTP_404_NOT_FOUND)


class GoldTradeViewSet(mixins.ListModelMixin,viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
    serializer_class = GoldTradeSerializer
    queryset = GoldTransaction.objects.none()
    
    def _trade(self, request, trade_type):
        user = request.user

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity_in_milligrams = serializer.validated_data['quantity']
        
        try:
            price_per_gram = Price.objects.latest('timestamp').price
        except Price.DoesNotExist:
            return Response({'error': 'Pricing unavailable.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        exact_value = (Decimal(quantity_in_milligrams) / Decimal(1000)) * Decimal(price_per_gram)
        final_rial_value = int(round(exact_value))

        with transaction.atomic():
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
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
    queryset = RialTransaction.objects.none()

    def get_serializer_class(self):
        if self.action in ['deposit', 'withdraw']:
            return RialTransactionActionSerializer
        return RialTransactionSerializer
    
    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        if self.action in ['deposit', 'withdraw']:
            user_accounts = BankAccount.objects.filter(
                user=self.request.user,
                status=BankAccount.VerificationStatus.VERIFIED
            )
            serializer.fields['bank_account'].queryset = user_accounts
        return serializer

    @action(detail=False, methods=['post'])
    def deposit(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        tx = RialTransaction.objects.create(
            user=request.user, 
            transaction_type='DEPOSIT', 
            amount=data['amount'], 
            status='PENDING',
            bank_account=data['bank_account']
        )
        response_serializer = RialTransactionSerializer(tx, context={'request': request})
        return Response({'message': 'Deposit request received', 'transaction': response_serializer.data}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'])
    def withdraw(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        with transaction.atomic():
            rial_wallet = RialWallet.objects.select_for_update().get(user=request.user)
            if rial_wallet.balance < data['amount']:
                return Response({'error': 'Insufficient funds'}, status=status.HTTP_400_BAD_REQUEST)
            
            rial_wallet.balance -= data['amount']
            rial_wallet.save()
            
            tx = RialTransaction.objects.create(
                user=request.user, 
                transaction_type='WITHDRAWAL', 
                amount=data['amount'], 
                status='PENDING',
                bank_account=data['bank_account']
            )
        response_serializer = RialTransactionSerializer(tx, context={'request': request})
        return Response({'message': 'Withdrawal request received', 'transaction': response_serializer.data}, status=status.HTTP_202_ACCEPTED)


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
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        timeframe = request.query_params.get('timeframe', 'daily')
        try:
            points_count = int(request.query_params.get('points', '100'))
            if points_count <= 1: points_count = 2 # Need at least 2 points
        except (ValueError, TypeError):
            points_count = 100

        end_date = timezone.now()
        
        if timeframe == 'weekly':
            start_date = end_date - timedelta(days=7)
        elif timeframe == 'monthly':
            start_date = end_date - timedelta(days=30)
        else: # 'daily'
            start_date = end_date - timedelta(days=1)
        
        queryset = Price.objects.filter(
            timestamp__gte=start_date
        ).order_by('timestamp')
        
        total_points_in_db = queryset.count()

        if total_points_in_db > points_count:
            all_pks = list(queryset.values_list('pk', flat=True))
            
            step = (total_points_in_db - 1) / (points_count - 1)
            
            sampled_indices = [int(round(i * step)) for i in range(points_count)]
            
            sampled_pks = [all_pks[i] for i in sampled_indices]
            
            sampled_queryset = Price.objects.filter(pk__in=sampled_pks).order_by('timestamp')
        else:
            sampled_queryset = queryset

        serializer = PriceSerializer(sampled_queryset, many=True)
        return Response(serializer.data)
    
class CustomAuthToken(ObtainAuthToken):
    renderer_classes = [BrowsableAPIRenderer, JSONRenderer]

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class UserBankAccountViewSet(viewsets.ModelViewSet):
    serializer_class = UserBankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AdminBankAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Allows admins to view all bank accounts and verify them.
    """
    serializer_class = AdminBankAccountSerializer
    permission_classes = [permissions.IsAdminUser]
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
    
class TicketViewSet(viewsets.ModelViewSet):
    """
    Allows users to create and manage their support tickets.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Ticket.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TicketCreateSerializer
        return TicketDetailSerializer
        
    def destroy(self, request, *args, **kwargs):
        """
        Allows a user to permanently delete their own ticket, but only if the
        status is 'OPEN'.
        """
        ticket = self.get_object()
        
        if ticket.status == Ticket.Status.OPEN:
            return super().destroy(request, *args, **kwargs)
        else:
            return Response(
                {'detail': 'You can only delete tickets that are still open.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
    def update(self, request, *args, **kwargs):
        """
        Allows a user to edit a ticket only if its status is 'OPEN'.
        """
        ticket = self.get_object()
        
        if ticket.status != Ticket.Status.OPEN:
            return Response(
                {'detail': 'You can only edit tickets that are still open.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
class UserVerificationView(generics.GenericAPIView):
    """
    GET: Shows the user's latest verification status.
    POST: Creates a new verification submission with a file upload.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    serializer_class = UserVerificationSubmitSerializer

    def get(self, request, *args, **kwargs):
        """Returns the status of the LATEST verification attempt."""
        latest_verification = UserVerification.objects.filter(user=request.user).last()
        
        if not latest_verification:
            return Response({'status': UserVerification.Status.NOT_SUBMITTED})
            
        serializer = UserVerificationSerializer(latest_verification)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """Creates a NEW verification submission."""
        latest_verification = UserVerification.objects.filter(user=request.user).last()
        
        if latest_verification and latest_verification.status in [UserVerification.Status.PENDING, UserVerification.Status.VERIFIED]:
            return Response(
                {'detail': 'You cannot submit a new verification while one is pending or already verified.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        serializer.save(
            user=request.user, 
            status=UserVerification.Status.PENDING,
            admin_notes=None
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminVerificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Allows admins to list, review, and approve/reject submissions.
    """
    permission_classes = [permissions.IsAdminUser]
    queryset = UserVerification.objects.filter(status=UserVerification.Status.PENDING)

    def get_serializer_class(self):
        if self.action == 'reject':
            return AdminRejectionSerializer
        if self.action == 'verify':
            return EmptySerializer
        return AdminVerificationSerializer

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Marks a submission as verified."""
        verification = self.get_object()
        verification.status = UserVerification.Status.VERIFIED
        verification.admin_notes = "Your document has been approved."
        verification.save()
        return Response({'status': 'Verification approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Marks a submission as rejected and adds a note."""
        verification = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        verification.status = UserVerification.Status.REJECTED
        verification.admin_notes = serializer.validated_data['admin_notes']
        verification.save()
        return Response({'status': 'Verification rejected'})
    
class TechnicalAnalysisView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        user_input = request.query_params.get('timeframe', '1d').lower()
        
        if user_input in ['weekly', '1w', '7d']:
            db_timeframe = '1W'
        else: # Default to daily
            db_timeframe = '1D'
            
        latest_analysis = TechnicalAnalysis.objects.filter(timeframe=db_timeframe).first()
        
        if latest_analysis:
            serializer = TechnicalAnalysisSerializer(latest_analysis)
            return Response(serializer.data)
        
        return Response(
            {"error": f"Analysis data for timeframe '{db_timeframe}' is not available yet."}, 
            status=status.HTTP_404_NOT_FOUND
        )
    

class SignalPredictionView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        horizon_param = request.query_params.get('horizon', 'daily').upper()
        
        horizon = PricePrediction.Horizon.DAILY
        if horizon_param == 'WEEKLY':
            horizon = PricePrediction.Horizon.WEEKLY
        
        try:
            prediction = PricePrediction.objects.get(horizon=horizon)
            serializer = SignalPredictionSerializer(prediction)
            return Response(serializer.data)
        except PricePrediction.DoesNotExist:
            return Response({"error": f"Prediction for {horizon} not available yet."}, status=404)
        

class AdminUserViewSet(viewsets.ModelViewSet):
    """
    An endpoint for admins to view, update, and soft-delete any user.
    """
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all()

class AdminGoldTransactionViewSet(viewsets.ModelViewSet):
    """
    An endpoint for admins to view, update, and delete any gold transaction.
    """
    serializer_class = AdminGoldTransactionSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = GoldTransaction.objects.all()
    filterset_class = GoldTransactionFilter

class AdminTicketViewSet(viewsets.ModelViewSet):
    """
    An endpoint for admins to view, filter, and manage all tickets.
    """
    serializer_class = AdminTicketSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Ticket.objects.all().order_by('-created_at')
    filterset_class = TicketFilter

class AdminFAQViewSet(viewsets.ModelViewSet):
    """
    An endpoint for admins to create, update, and manage all FAQs.
    """
    serializer_class = AdminFAQSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = FAQ.all_objects.all().order_by('sort_order')

class ReportingDashboardView(APIView):
    """
    An admin-only endpoint that provides a summary report of platform activity.
    Can be filtered by a 'period' query parameter: daily, monthly, yearly.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        period = request.query_params.get('period', None)
        end_date = timezone.now()
        start_date = None

        if period == 'daily':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'monthly':
            start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'yearly':
            start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        transactions = GoldTransaction.objects.all()
        if start_date:
            transactions = transactions.filter(timestamp__gte=start_date)

        total_gold_bought = transactions.filter(transaction_type='BUY').aggregate(total=Sum('quantity'))['total'] or 0
        total_gold_sold = transactions.filter(transaction_type='SELL').aggregate(total=Sum('quantity'))['total'] or 0
        total_fees = transactions.aggregate(total=Sum('fees'))['total'] or 0
        
        total_rial_in_wallets = RialWallet.objects.aggregate(total=Sum('balance'))['total'] or 0
        total_gold_in_wallets = GoldWallet.objects.aggregate(total=Sum('balance'))['total'] or 0
        
        data = {
            'report_period': period or 'all_time',
            'total_gold_bought_mg': total_gold_bought,
            'total_gold_sold_mg': total_gold_sold,
            'total_fees_earned_rials': total_fees,
            'current_total_rial_in_wallets': total_rial_in_wallets,
            'current_total_gold_in_wallets_mg': total_gold_in_wallets,
        }
        
        return Response(data)
    
class AdminRialTransactionViewSet(viewsets.ModelViewSet):
    """
    An endpoint for admins to view, filter, and manage all Rial transactions.
    """
    serializer_class = AdminRialTransactionSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = RialTransaction.objects.all().order_by('-timestamp')
    filterset_class = RialTransactionFilter

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approves a pending transaction and updates the user's wallet."""
        transaction_obj = self.get_object()
        if transaction_obj.status != 'PENDING':
            return Response({'error': 'This transaction is not pending.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if transaction_obj.transaction_type == 'DEPOSIT':
                wallet = RialWallet.objects.select_for_update().get(user=transaction_obj.user)
                wallet.balance += transaction_obj.amount
                wallet.save()
            
            transaction_obj.status = 'COMPLETED'
            transaction_obj.save()
            
        return Response({'status': f"Transaction {transaction_obj.id} approved."})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Rejects a pending transaction and refunds the user if it was a withdrawal."""
        transaction_obj = self.get_object()
        if transaction_obj.status != 'PENDING':
            return Response({'error': 'This transaction is not pending.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if transaction_obj.transaction_type == 'WITHDRAWAL':
                wallet = RialWallet.objects.select_for_update().get(user=transaction_obj.user)
                wallet.balance += transaction_obj.amount
                wallet.save()

            transaction_obj.status = 'FAILED'
            transaction_obj.save()

        return Response({'status': f"Transaction {transaction_obj.id} rejected."})