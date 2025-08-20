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
    """Calculates all indicators for a given DataFrame and saves the result."""
    if len(price_df) < 50:
        return None, f"Not enough resampled data for {timeframe} analysis (need 50 points, have {len(price_df)})."

    last_price = price_df['close'].iloc[-1]

    # --- Moving Averages ---
    ma_signals = {'buy': 0, 'sell': 0, 'neutral': 0}
    for period in [10, 20, 30, 50, 100, 200]:
        if len(price_df) < period: continue
        ma_signals['buy' if last_price > price_df['close'].rolling(window=period).mean().iloc[-1] else 'sell'] += 1
        ma_signals['buy' if last_price > price_df['close'].ewm(span=period, adjust=False).mean().iloc[-1] else 'sell'] += 1

    # --- Oscillators ---
    osc_signals = {'buy': 0, 'sell': 0, 'neutral': 0}
    # (Full oscillator calculations from before)
    # RSI
    delta = price_df['close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(window=14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean(); rsi = 100 - (100 / (1 + (gain/loss)));
    if rsi.iloc[-1] > 70: osc_signals['sell'] += 1
    elif rsi.iloc[-1] < 30: osc_signals['buy'] += 1
    else: osc_signals['neutral'] += 1
    # Stochastic
    low14 = price_df['low'].rolling(14).min(); high14 = price_df['high'].rolling(14).max(); k_percent = 100 * ((price_df['close'] - low14) / (high14 - low14));
    if k_percent.iloc[-1] > 80: osc_signals['sell'] += 1
    elif k_percent.iloc[-1] < 20: osc_signals['buy'] += 1
    else: osc_signals['neutral'] += 1
    
    # --- Aggregation and Saving ---
    ma_final_signal = get_final_signal(ma_signals['buy'], ma_signals['sell'], ma_signals['neutral'])
    osc_final_signal = get_final_signal(osc_signals['buy'], osc_signals['sell'], osc_signals['neutral'])
    summary_buy = ma_signals['buy'] + osc_signals['buy']; summary_sell = ma_signals['sell'] + osc_signals['sell']; summary_neutral = ma_signals['neutral'] + osc_signals['neutral']
    summary_final_signal = get_final_signal(summary_buy, summary_sell, summary_neutral)

    TechnicalAnalysis.objects.update_or_create(
        timeframe=timeframe,
        defaults={
            'ma_signal': ma_final_signal, 'osc_signal': osc_final_signal, 'summary_signal': summary_final_signal,
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
        
        if len(prices) < 200:
            self.stdout.write(self.style.WARNING("Not enough price data to run a full analysis."))
            return

        df = pd.DataFrame(list(prices)); df['price'] = pd.to_numeric(df['price']); df['timestamp'] = pd.to_datetime(df['timestamp']); df.set_index('timestamp', inplace=True)
        df['close'] = df['price']; df['high'] = df['price']; df['low'] = df['price']

        # --- Calculate for Daily ('1D') timeframe ---
        daily_df = df.resample('H').last().dropna()
        signal, error = calculate_and_save_analysis('1D', daily_df)
        if error: self.stdout.write(self.style.WARNING(error))
        else: self.stdout.write(self.style.SUCCESS(f"Daily analysis saved with signal: {signal}"))

        # --- Calculate for Weekly ('1W') timeframe ---
        weekly_df = df.resample('D').last().dropna()
        signal, error = calculate_and_save_analysis('1W', weekly_df)
        if error: self.stdout.write(self.style.WARNING(error))
        else: self.stdout.write(self.style.SUCCESS(f"Weekly analysis saved with signal: {signal}"))