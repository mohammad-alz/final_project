# api/management/commands/calculate_indicators.py
import pandas as pd
from django.core.management.base import BaseCommand
from api.models import Price, TechnicalAnalysis

def get_final_signal(buy, sell, neutral):
    """Helper function to determine the final signal from counts."""
    if buy > sell * 2: return TechnicalAnalysis.Signal.STRONG_BUY
    if sell > buy * 2: return TechnicalAnalysis.Signal.STRONG_SELL
    if buy > sell: return TechnicalAnalysis.Signal.BUY
    if sell > buy: return TechnicalAnalysis.Signal.SELL
    return TechnicalAnalysis.Signal.NEUTRAL

def calculate_and_save_analysis(timeframe, price_df):
    """
    Calculates all indicators for a given DataFrame and saves the result.
    """
    if len(price_df) < 50: # Need enough data points for the analysis
        return None, f"Not enough data for {timeframe} analysis."

    last_price = price_df['close'].iloc[-1]

    # --- 1. Moving Averages ---
    ma_signals = {'buy': 0, 'sell': 0, 'neutral': 0}
    ma_periods = [10, 20, 30, 50, 100, 200]
    for period in ma_periods:
        if len(price_df) < period: continue # Skip if not enough data
        sma = price_df['close'].rolling(window=period).mean().iloc[-1]
        ema = price_df['close'].ewm(span=period, adjust=False).mean().iloc[-1]
        ma_signals['buy' if last_price > sma else 'sell'] += 1
        ma_signals['buy' if last_price > ema else 'sell'] += 1

    # --- 2. Oscillators ---
    osc_signals = {'buy': 0, 'sell': 0, 'neutral': 0}
    # ... (Add your oscillator calculation logic here, e.g., RSI, MACD, etc.)
    # For brevity, I'll add a placeholder, but you should use the full version
    delta = price_df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = 100 - (100 / (1 + (gain / loss)))
    if rsi.iloc[-1] > 70: osc_signals['sell'] += 1
    elif rsi.iloc[-1] < 30: osc_signals['buy'] += 1
    else: osc_signals['neutral'] += 1

    # --- 3. Aggregate and Determine Signals ---
    summary_buy = ma_signals['buy'] + osc_signals['buy']
    summary_sell = ma_signals['sell'] + osc_signals['sell']
    summary_neutral = ma_signals['neutral'] + osc_signals['neutral']

    ma_final_signal = get_final_signal(ma_signals['buy'], ma_signals['sell'], ma_signals['neutral'])
    osc_final_signal = get_final_signal(osc_signals['buy'], osc_signals['sell'], osc_signals['neutral'])
    summary_final_signal = get_final_signal(summary_buy, summary_sell, summary_neutral)

    # --- Save the results ---
    TechnicalAnalysis.objects.update_or_create(
        timeframe=timeframe, 
        defaults={
            'ma_signal': ma_final_signal,
            'osc_signal': osc_final_signal,
            'summary_signal': summary_final_signal,
            'ma_buy_count': ma_signals['buy'], 'ma_sell_count': ma_signals['sell'], 'ma_neutral_count': ma_signals['neutral'],
            'osc_buy_count': osc_signals['buy'], 'osc_sell_count': osc_signals['sell'], 'osc_neutral_count': osc_signals['neutral'],
            'summary_buy_count': summary_buy, 'summary_sell_count': summary_sell, 'summary_neutral_count': summary_neutral,
        }
    )
    return summary_final_signal, None

class Command(BaseCommand):
    help = 'Calculates and saves technical analysis for multiple timeframes.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Fetching price data...")
        prices = Price.objects.all().order_by('timestamp').values('timestamp', 'price')
        
        if not prices:
            self.stdout.write(self.style.WARNING("No price data found."))
            return

        df = pd.DataFrame(list(prices))
        df['price'] = pd.to_numeric(df['price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df['close'] = df['price']

        # --- Calculate for Daily ('1D') timeframe ---
        # Get data from the last 24 hours, resampled hourly
        daily_df = df[df.index > (df.index.max() - pd.Timedelta(days=1))].resample('H').last().dropna()
        signal, error = calculate_and_save_analysis('1D', daily_df)
        if error: self.stdout.write(self.style.WARNING(error))
        else: self.stdout.write(self.style.SUCCESS(f"Daily analysis saved with signal: {signal}"))

        # --- Calculate for Weekly ('1W') timeframe ---
        # Get data from the last 7 days, also resampled hourly
        weekly_df = df[df.index > (df.index.max() - pd.Timedelta(days=7))].resample('H').last().dropna()
        signal, error = calculate_and_save_analysis('1W', weekly_df)
        if error: self.stdout.write(self.style.WARNING(error))
        else: self.stdout.write(self.style.SUCCESS(f"Weekly analysis saved with signal: {signal}"))