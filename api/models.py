from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import RegexValidator
# --- Soft Delete Manager ---
# This custom manager will automatically filter out objects marked as inactive.
class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

# --- Core Models ---

class User(AbstractUser):
    birth_date = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=20, unique=True)
    ref_code = models.CharField(max_length=10, blank=True, null=True)
    phone_number = models.CharField(max_length=11, unique=True)
    
    def __str__(self): return self.username

    def delete(self, using=None, keep_parents=False):
        """Soft deletes the user by setting is_active to False."""
        self.is_active = False
        self.save()

class GoldWallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, related_name='gold_wallet')
    balance = models.BigIntegerField(default=0) # Stored in Milligrams
    def __str__(self): return f"{self.user.username}'s Gold Wallet ({self.balance} mg)"

class RialWallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, related_name='rial_wallet')
    balance = models.BigIntegerField(default=0)
    def __str__(self): return f"{self.user.username}'s Rial Wallet ({self.balance} Rials)"

@receiver(post_save, sender=User)
def create_user_wallets(sender, instance, created, **kwargs):
    if created:
        GoldWallet.objects.create(user=instance)
        RialWallet.objects.create(user=instance)

class GoldTransaction(models.Model):
    class TransactionType(models.TextChoices): BUY = 'BUY', 'Buy'; SELL = 'SELL', 'Sell'
    class Status(models.TextChoices): COMPLETED = 'COMPLETED', 'Completed'; PENDING = 'PENDING', 'Pending'; FAILED = 'FAILED', 'Failed'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='gold_transactions'); transaction_type = models.CharField(max_length=4, choices=TransactionType.choices); quantity = models.BigIntegerField(); price_per_unit = models.BigIntegerField(); total_price = models.BigIntegerField(); fees = models.BigIntegerField(default=0); net_amount = models.BigIntegerField(); timestamp = models.DateTimeField(auto_now_add=True); status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING); notes = models.TextField(blank=True, null=True)


class Price(models.Model):
    price = models.BigIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

# --- FAQ Model with Soft Delete ---
class FAQ(models.Model):
    question = models.TextField()
    answer = models.TextField()
    sort_order = models.IntegerField(default=0)
    
    # 1. The field to track status. Renamed from is_published for clarity.
    is_active = models.BooleanField(default=True)

    # 2. The managers to handle querying.
    objects = SoftDeleteManager() # Default manager only shows active FAQs.
    all_objects = models.Manager() # A second manager to access all FAQs.

    # 3. Overridden delete() method.
    def delete(self, using=None, keep_parents=False):
        """Soft deletes the object."""
        self.is_active = False
        self.save()

    def restore(self):
        """Restores a soft-deleted object."""
        self.is_active = True
        self.save()
    
    def __str__(self):
        return self.question

class License(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    image_url = models.URLField()
    issue_date = models.DateField(blank=True, null=True)
    expire_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, default='ACTIVE')
    
    # 1. The field to track status. Renamed from is_published for clarity.
    is_active = models.BooleanField(default=True)

    # 2. The managers to handle querying.
    objects = SoftDeleteManager() # Default manager only shows active FAQs.
    all_objects = models.Manager() # A second manager to access all FAQs.

    # 3. Overridden delete() method.
    def delete(self, using=None, keep_parents=False):
        """Soft deletes the object."""
        self.is_active = False
        self.save()

    def restore(self):
        """Restores a soft-deleted object."""
        self.is_active = True
        self.save()

class BankAccount(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bank_accounts')
    bank_name = models.CharField(max_length=100)

    card_number_validator = RegexValidator(
        regex=r'^\d{16}$',
        message="Card number must be exactly 16 digits."
    )
    card_number = models.CharField(
        validators=[card_number_validator], 
        max_length=16, 
        unique=True
    )
    status = models.CharField(
        max_length=10, 
        choices=VerificationStatus.choices, 
        default=VerificationStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.card_number}"
    
class RialTransaction(models.Model):
    bank_account = models.ForeignKey(
        BankAccount, 
        on_delete=models.SET_NULL, # If account is deleted, keep the transaction record
        null=True, 
        blank=True
    )
    class TransactionType(models.TextChoices): DEPOSIT = 'DEPOSIT', 'Deposit'; WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal'
    class Status(models.TextChoices): COMPLETED = 'COMPLETED', 'Completed'; PENDING = 'PENDING', 'Pending'; FAILED = 'FAILED', 'Failed'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rial_transactions'); transaction_type = models.CharField(max_length=10, choices=TransactionType.choices); amount = models.BigIntegerField(); timestamp = models.DateTimeField(auto_now_add=True); status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING); bank_transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True); notes = models.TextField(blank=True, null=True)