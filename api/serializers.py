from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import (
    User, GoldWallet, RialWallet, GoldTransaction, RialTransaction,
    Price, FAQ, License, BankAccount
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
    

class BankAccountSerializer(serializers.ModelSerializer):
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

class EmptySerializer(serializers.Serializer):
    pass

class RialTransactionSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    bank_account = BankAccountSerializer(read_only=True)
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