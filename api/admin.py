from django.contrib import admin
from .models import (
    User, GoldWallet, RialWallet, GoldTransaction,
    RialTransaction, Price, FAQ, License, BankAccount,
    Ticket, TicketAttachment, UserVerification,
    TechnicalAnalysis,
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

class TicketAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'description', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority')
    search_fields = ('user__username', 'title')
    readonly_fields = ('user', 'title', 'description')

class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'ticket__user', 'file', 'uploaded_at')
    search_fields = ('ticket__user__username', 'ticket__id')
    readonly_fields = ('ticket',)

class UserVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'image', 'submitted_at')
    list_filter = ('status',)
    readonly_fields = ('image', 'user')

class TechnicalAnalysisAdmin(admin.ModelAdmin):
    list_display = ('summary_signal', 'calculated_at')
    list_filter = ('summary_signal',)
    readonly_fields = (
        'ma_buy_count',
        'ma_sell_count',
        'ma_neutral_count',
        'osc_buy_count',
        'osc_sell_count',
        'osc_neutral_count',
        'summary_buy_count',
        'summary_sell_count',
        'summary_neutral_count',
        'summary_signal',
        'calculated_at')
    

admin.site.register(User, UserAdmin)
admin.site.register(GoldWallet, GoldWalletAdmin)
admin.site.register(RialWallet, RialWalletAdmin)
admin.site.register(GoldTransaction, GoldTransactionAdmin)
admin.site.register(RialTransaction, RialTransactionAdmin)
admin.site.register(Price, PriceAdmin)
admin.site.register(FAQ, FAQAdmin)
admin.site.register(License, LicenseAdmin)
admin.site.register(BankAccount, BankAccountAdmin)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(TicketAttachment, TicketAttachmentAdmin)
admin.site.register(UserVerification, UserVerificationAdmin)
admin.site.register(TechnicalAnalysis, TechnicalAnalysisAdmin)