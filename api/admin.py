from django.contrib import admin
from .models import (
    User, GoldWallet, RialWallet, GoldTransaction,
    RialTransaction, Price, FAQ, License, BankAccount
)

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email')

class GoldWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user__username',)

class RialWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user__username',)

class GoldTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'quantity', 'status', 'timestamp')
    list_filter = ('status', 'transaction_type', 'timestamp')
    search_fields = ('user__username',)

class RialTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'status', 'timestamp', 'bank_account')
    list_filter = ('status', 'transaction_type', 'timestamp')
    search_fields = ('user__username','bank_account')

class PriceAdmin(admin.ModelAdmin):
    list_display = ('price', 'timestamp')
    ordering = ('-timestamp',)

class FAQAdmin(admin.ModelAdmin):
    # Display the active status in the list
    list_display = ('question', 'sort_order', 'is_active')
    # Add a filter for the active status
    list_filter = ('is_active',)
    
    def get_queryset(self, request):
        # Tell the admin to use the all_objects manager to show all items
        return FAQ.all_objects.all()
    
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'is_active', 'expire_date')
    list_filter = ('is_active', 'status')
    search_fields = ('name',)
    
    def get_queryset(self, request):
        # Tell the admin to use the all_objects manager to show all items
        return License.all_objects.all()
    
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'bank_name', 'card_number', 'status', 'created_at')
    list_filter = ('status', 'bank_name')
    search_fields = ('user__username', 'card_number')
    readonly_fields = ('user',)
    
admin.site.register(User, UserAdmin)
admin.site.register(GoldWallet, GoldWalletAdmin)
admin.site.register(RialWallet, RialWalletAdmin)
admin.site.register(GoldTransaction, GoldTransactionAdmin)
admin.site.register(RialTransaction, RialTransactionAdmin)
admin.site.register(Price, PriceAdmin)
admin.site.register(FAQ, FAQAdmin)
admin.site.register(License, LicenseAdmin)
admin.site.register(BankAccount, BankAccountAdmin)