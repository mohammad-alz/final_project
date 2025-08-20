from django.contrib.staticfiles.storage import staticfiles_storage
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import (
    User, GoldWallet, RialWallet, GoldTransaction, RialTransaction,
    Price, FAQ, License, BankAccount, Ticket, TicketAttachment,
    UserVerification,
)

class GoldWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoldWallet
        fields = ['user', 'balance'] # Shows balance in milligrams

class RialWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = RialWallet
        fields = ['user', 'balance'] # Shows balance in whole Rials

class UserSerializer(serializers.ModelSerializer):
    gold_wallet = GoldWalletSerializer(read_only=True)
    rial_wallet = RialWalletSerializer(read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone_number', 'birth_date', 'national_id', 'gold_wallet', 'rial_wallet', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class PriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = ['price', 'timestamp']

class GoldTransactionSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    class Meta:
        model = GoldTransaction
        fields = '__all__' # Shows quantity in milligrams


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer']

class LicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = License
        fields = '__all__'

class AdminLicenseSerializer(serializers.ModelSerializer):
    # --- RENAME THIS FIELD ---
    # This field creates the clickable link to the API detail page
    api_url = serializers.HyperlinkedIdentityField(view_name='api:admin-license-detail')

    class Meta:
        model = License
        # Add 'api_url' and also include the original 'url' from the model
        fields = ['api_url', 'id', 'name', 'description', 'url', 'image', 'issue_date', 'expire_date', 'status', 'is_active']

class GoldTradeSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=1, 
        help_text="The amount of gold to trade in milligrams."
    )

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add all the custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['phone_number'] = user.phone_number

        return token
    

class AdminBankAccountSerializer(serializers.ModelSerializer):
    # This new field creates the clickable link
    url = serializers.HyperlinkedIdentityField(
        view_name='api:admin-bank-account-detail',
        lookup_field='pk'
    )
    
    class Meta:
        model = BankAccount
        read_only_fields = ['user', 'status']
        # Add 'url' to the beginning of the fields list
        fields = ['url', 'id', 'bank_name', 'card_number', 'status', 'user']

BANK_LOGOS = {
    'mli': 'api/images/bank_logos/mli.png',
    'maaaa3can': 'api/images/bank_logos/maaaa3can.png',
    'beeeluuu': 'api/images/bank_logos/pasargad.png',
    # Add all other bank names and their logo filenames here
}

class UserBankAccountSerializer(serializers.ModelSerializer):
    # This new field will contain the URL to the bank's logo
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = BankAccount
        read_only_fields = ['user', 'status']
        # Add 'logo_url' to the fields list
        fields = ['id', 'bank_name', 'card_number', 'status', 'logo_url']

    def get_logo_url(self, obj):
        # Look up the logo file from our dictionary
        logo_path = BANK_LOGOS.get(obj.bank_name)
        if logo_path:
            # Return the full URL to the static file
            return self.context['request'].build_absolute_uri(
                staticfiles_storage.url(logo_path)
            )
        return None

class EmptySerializer(serializers.Serializer):
    pass

class RialTransactionSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    bank_account = UserBankAccountSerializer(read_only=True)
    class Meta:
        model = RialTransaction
        fields = '__all__'

class RialTransactionActionSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)
    # This field will render as a dropdown of the user's bank accounts
    bank_account = serializers.PrimaryKeyRelatedField(
        queryset=BankAccount.objects.all(),
        help_text="Select one of your verified bank accounts."
    )

class TicketAnswerSerializer(serializers.Serializer):
    answer = serializers.CharField()

class TicketAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketAttachment
        fields = ['id', 'file', 'uploaded_at']

class TicketDetailSerializer(serializers.ModelSerializer):
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    answered_by = serializers.StringRelatedField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='api:ticket-detail')

    class Meta:
        model = Ticket
        fields = ['url', 'id', 'title', 'description', 'priority', 'status', 'created_at', 'attachments', 'answer', 'answered_at', 'answered_by']

# --- NEW: This serializer is for CREATING/UPDATING a ticket ---
class TicketCreateSerializer(serializers.ModelSerializer):
    uploaded_attachments = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False),
        write_only=True, required=False
    )

    class Meta:
        model = Ticket
        # Notice 'status' is NOT in this list
        fields = ['title', 'description', 'priority', 'uploaded_attachments']

    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_attachments', [])
        # The status will be set to its default value ('OPEN') automatically
        ticket = Ticket.objects.create(**validated_data)
        for file in uploaded_files:
            TicketAttachment.objects.create(ticket=ticket, file=file)
        return ticket
    

# This serializer is now just for submitting an image
class UserVerificationSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserVerification
        fields = ['image']

# This serializer is for displaying the status of the latest submission
class UserVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserVerification
        fields = ['status', 'image', 'admin_notes', 'submitted_at']

# Serializer for the admin to update the status
class AdminRejectionSerializer(serializers.Serializer):
    admin_notes = serializers.CharField(style={'base_template': 'textarea.html'})

# --- UPDATE the AdminVerificationSerializer ---
class AdminVerificationSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    # This field creates the clickable link to the detail page
    url = serializers.HyperlinkedIdentityField(view_name='api:admin-verification-detail')
    
    class Meta:
        model = UserVerification
        # Add 'url' to the fields list
        fields = ['url', 'id', 'user_email', 'status', 'image', 'admin_notes', 'submitted_at']
        read_only_fields = ['image', 'submitted_at', 'user_email']

