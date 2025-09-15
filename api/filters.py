from django_filters import rest_framework as filters
from .models import (
    GoldTransaction, Ticket, RialTransaction,
    
)

class GoldTransactionFilter(filters.FilterSet):
    class Meta:
        model = GoldTransaction
        fields = ['user']

class TicketFilter(filters.FilterSet):
    class Meta:
        model = Ticket
        fields = ['user', 'status', 'priority']

class RialTransactionFilter(filters.FilterSet):
    class Meta:
        model = RialTransaction
        fields = ['user', 'status', 'transaction_type']

