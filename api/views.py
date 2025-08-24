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
    TechnicalAnalysis,
)
from .serializers import (
    UserSerializer, GoldTransactionSerializer, RialTransactionSerializer,
    PriceSerializer, FAQSerializer, LicenseSerializer,GoldTradeSerializer,
    MyTokenObtainPairSerializer, UserBankAccountSerializer, AdminBankAccountSerializer,
    EmptySerializer, RialTransactionActionSerializer, TicketCreateSerializer,
    TicketDetailSerializer, TicketAnswerSerializer, UserVerificationSerializer,
    AdminVerificationSerializer, UserVerificationSubmitSerializer,
    AdminRejectionSerializer, AdminLicenseSerializer, TechnicalAnalysisSerializer,
    UserCreateSerializer
)

from .permissions import IsVerifiedUser

# --- User and Public Views ---

class UserViewSet(viewsets.ModelViewSet):
    """
    Handles user creation (registration) and profile viewing/updating.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only see/edit their own profile
        return self.queryset.filter(pk=self.request.user.pk)

    def get_permissions(self):
        # The 'create' action (registration) is public
        if self.action == 'create':
            self.permission_classes = [permissions.AllowAny]
        return super().get_permissions()
        
    def get_serializer_class(self):
        # For the 'create' action, use the new registration serializer
        if self.action == 'create':
            return UserCreateSerializer
        # For all other actions (GET, PUT, PATCH), use the display serializer
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
    # Admins should be able to see all licenses, including inactive ones
    queryset = License.all_objects.all()
    # Required for the image upload
    parser_classes = [MultiPartParser, FormParser]

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
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
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
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
    queryset = RialTransaction.objects.none()

    def get_serializer_class(self):
        # Use our new input serializer for the deposit and withdraw actions
        if self.action in ['deposit', 'withdraw']:
            return RialTransactionActionSerializer
        # Use the default serializer for other actions (like the list view)
        return RialTransactionSerializer
    
    def get_serializer(self, *args, **kwargs):
        # This method dynamically filters the queryset for the dropdown field
        serializer = super().get_serializer(*args, **kwargs)
        if self.action in ['deposit', 'withdraw']:
            # Get only the current user's VERIFIED bank accounts
            user_accounts = BankAccount.objects.filter(
                user=self.request.user,
                status=BankAccount.VerificationStatus.VERIFIED
            )
            # Apply this filtered queryset to the dropdown field
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
        return Response({'message': 'Deposit request received', 'transaction': RialTransactionSerializer(tx).data}, status=status.HTTP_202_ACCEPTED)

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
        
        # 1. Get the full queryset for the time range
        queryset = Price.objects.filter(
            timestamp__gte=start_date
        ).order_by('timestamp')
        
        # 2. Perform sampling only if necessary
        total_points_in_db = queryset.count()

        if total_points_in_db > points_count:
            # Get a list of all the primary keys (IDs) in the queryset
            all_pks = list(queryset.values_list('pk', flat=True))
            
            # Calculate a floating-point step
            step = (total_points_in_db - 1) / (points_count - 1)
            
            # Find the indices of the points we want to pick
            sampled_indices = [int(round(i * step)) for i in range(points_count)]
            
            # Get the primary keys (IDs) at those specific indices
            sampled_pks = [all_pks[i] for i in sampled_indices]
            
            # Fetch only the objects with those specific IDs
            sampled_queryset = Price.objects.filter(pk__in=sampled_pks).order_by('timestamp')
        else:
            # If we don't have enough data to sample, return it all
            sampled_queryset = queryset

        serializer = PriceSerializer(sampled_queryset, many=True)
        return Response(serializer.data)
    
class CustomAuthToken(ObtainAuthToken):
    renderer_classes = [BrowsableAPIRenderer, JSONRenderer]

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class UserBankAccountViewSet(viewsets.ModelViewSet):
    # Use the new, simpler serializer that has no URL field
    serializer_class = UserBankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# --- View for ADMINS to manage all accounts ---
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
    # Add parsers to handle file uploads
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        # A user can only see their own tickets
        return Ticket.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Automatically assign the ticket to the logged-in user
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TicketCreateSerializer
        # For 'list', 'retrieve', etc., use the detail serializer
        return TicketDetailSerializer
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def answer(self, request, pk=None):
        """
        Allows an admin to post an answer to a ticket.
        """
        ticket = self.get_object()
        serializer = TicketAnswerSerializer(data=request.data)
        
        if serializer.is_valid():
            ticket.answer = serializer.validated_data['answer']
            ticket.answered_by = request.user
            ticket.answered_at = timezone.now()
            ticket.status = Ticket.Status.CLOSED # Optionally close the ticket
            ticket.save()
            # Return the full, updated ticket details
            return Response(TicketDetailSerializer(ticket).data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def destroy(self, request, *args, **kwargs):
        """
        Allows a user to permanently delete their own ticket, but only if the
        status is 'OPEN'.
        """
        ticket = self.get_object()
        
        if ticket.status == Ticket.Status.OPEN:
            # This calls the original method to permanently delete the object
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
        
        # If the status is OPEN, proceed with the normal update logic
        return super().update(request, *args, **kwargs)
    
class UserVerificationView(generics.GenericAPIView):
    """
    GET: Shows the user's latest verification status.
    POST: Creates a new verification submission with a file upload.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    # This tells the view (and the browsable API) which serializer to use for POST
    serializer_class = UserVerificationSubmitSerializer

    def get(self, request, *args, **kwargs):
        """Returns the status of the LATEST verification attempt."""
        latest_verification = UserVerification.objects.filter(user=request.user).last()
        
        if not latest_verification:
            return Response({'status': UserVerification.Status.NOT_SUBMITTED})
            
        # For displaying the status, we still use the detailed serializer
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
            
        # Use the get_serializer() method provided by GenericAPIView
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create a new verification object
        serializer.save(
            user=request.user, 
            status=UserVerification.Status.PENDING,
            admin_notes=None
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# --- View for ADMINS to manage all submissions ---
class AdminVerificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Allows admins to list, review, and approve/reject submissions.
    """
    permission_classes = [permissions.IsAdminUser]
    queryset = UserVerification.objects.filter(status=UserVerification.Status.PENDING)

    def get_serializer_class(self):
        if self.action == 'reject':
            return AdminRejectionSerializer
        # --- ADD THIS CHECK ---
        # For the 'verify' action, we don't need any input fields.
        if self.action == 'verify':
            return EmptySerializer
        # For all other actions (like list/retrieve), use the main serializer.
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
        # Get the timeframe from the URL, default to '1D' (daily)
        user_input = request.query_params.get('timeframe', '1d').lower()
        
        # Map the user's input to the timeframe stored in the database ('1D' or '1W')
        if user_input in ['weekly', '1w', '7d']:
            db_timeframe = '1W'
        else: # Default to daily
            db_timeframe = '1D'
            
        # Get the analysis for the mapped timeframe
        latest_analysis = TechnicalAnalysis.objects.filter(timeframe=db_timeframe).first()
        # --- END OF FIX ---
        
        if latest_analysis:
            serializer = TechnicalAnalysisSerializer(latest_analysis)
            return Response(serializer.data)
        
        return Response(
            {"error": f"Analysis data for timeframe '{db_timeframe}' is not available yet."}, 
            status=status.HTTP_404_NOT_FOUND
        )