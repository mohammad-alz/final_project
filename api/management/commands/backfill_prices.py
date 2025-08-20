import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import Price

class Command(BaseCommand):
    help = 'Backfills historical price data, leading up to the earliest existing record.'

    def handle(self, *args, **kwargs):
        oldest_record = Price.objects.order_by('timestamp').first()

        if not oldest_record:
            self.stdout.write(self.style.ERROR("No existing price data found. Cannot backfill."))
            return

        self.stdout.write("Starting to backfill historical price data...")

        price_history = []
        # The exact time and price of your first real record
        end_timestamp = oldest_record.timestamp
        # We start our fake history based on the price of your first real record
        current_price = float(oldest_record.price)

        # How far back to generate data
        num_days_to_generate = 200
        start_timestamp = end_timestamp - timedelta(days=num_days_to_generate)
        
        # We go forward in time from 200 days ago up to your first record
        current_timestamp = start_timestamp
        while current_timestamp < end_timestamp:
            price_history.append(
                Price(timestamp=current_timestamp, price=int(current_price))
            )
            # Fluctuate the price for the next data point
            change = random.uniform(-0.0001, 0.0001)
            current_price = current_price * (1 + change)
            # Move forward 2 minutes in time
            current_timestamp += timedelta(minutes=2)

        # Save all new records in one go
        Price.objects.bulk_create(price_history)

        self.stdout.write(self.style.SUCCESS(
            f"Successfully created {len(price_history)} historical price records."
        ))