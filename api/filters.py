from django_filters import rest_framework as filters
from .models import (
    GoldTransaction, Ticket, RialTransaction,
    
)

class GoldTransactionFilter(filters.FilterSet):
    class Meta:
        model = GoldTransaction
        # Define the fields you want to be able to filter on
        fields = ['user']

class TicketFilter(filters.FilterSet):
    class Meta:
        model = Ticket
        # Define the fields you want to filter on
        fields = ['user', 'status', 'priority']

class RialTransactionFilter(filters.FilterSet):
    class Meta:
        model = RialTransaction
        fields = ['user', 'status', 'transaction_type']

