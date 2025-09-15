import requests
import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from api.models import Price
import pprint


class Command(BaseCommand):
    help = 'Fetches the latest 18k gold price from BrsApi.ir and saves it to the database in Rials.'

    def handle(self, *args, **kwargs):
        api_key = getattr(settings, 'BRS_API_KEY', None)
        if not api_key:
            raise CommandError('Please set BRS_API_KEY in your settings.py file.')

        url = f"https://BrsApi.ir/Api/Market/Gold_Currency.php?key={api_key}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }

        self.stdout.write("Connecting to API to get the latest gold price...")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if isinstance(data, dict):
                gold_list = data.get('gold', [])
            elif isinstance(data, list):
                gold_list = data
            else:
                raise CommandError("API response is in an unexpected format.")

            price_in_toman = None
            for item in gold_list:
                if isinstance(item, dict) and item.get('symbol') == 'IR_GOLD_18K':
                    price_in_toman = int(item.get('price'))
                    break
            
            if price_in_toman is not None:
                price_in_rials = price_in_toman * 10
                Price.objects.create(price=price_in_rials)
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully fetched and saved new 18k gold price: {price_in_rials} Rials'
                ))
            else:
                raise CommandError('18K gold price (IR_GOLD_18K) not found in the API response.')

        except requests.exceptions.RequestException as e:
            raise CommandError(f'Network error: {e}')
        except json.JSONDecodeError:
            raise CommandError('Error processing the server response. It might not be valid JSON.')
        except Exception as e:
            raise CommandError(f'An unexpected error occurred: {e}')