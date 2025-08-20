import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import Price

class Command(BaseCommand):
    help = 'Backfills historical price data from the earliest existing record.'

    def handle(self, *args, **kwargs):
        # 1. Find the oldest price record in the database
        oldest_price_record = Price.objects.order_by('timestamp').first()

        if not oldest_price_record:
            self.stdout.write(self.style.ERROR("Database has no price data. Cannot backfill. Please run 'update_gold_price' first."))
            return

        start_time = oldest_price_record.timestamp
        current_price = oldest_price_record.price
        
        self.stdout.write(f"Oldest price found at {start_time}. Starting backfill from this point.")
        
        price_list_to_create = []
        num_days_to_backfill = 200
        points_per_day = 24 * 30 # One point every 2 minutes
        total_points = num_days_to_backfill * points_per_day

        # 2. Loop backwards in time from the oldest record
        for i in range(1, total_points + 1):
            timestamp = start_time - timedelta(minutes=i * 2)
            
            # Create a small random fluctuation
            change = random.uniform(-0.0001, 0.0001) # Smaller, more realistic fluctuation
            current_price = float(current_price) * (1 + change)
            
            price_list_to_create.append(
                Price(timestamp=timestamp, price=int(current_price))
            )

        # 3. Save all the new historical data in one efficient query
        Price.objects.bulk_create(price_list_to_create)

        self.stdout.write(self.style.SUCCESS(
            f"Successfully created {len(price_list_to_create)} new historical price records."
        ))