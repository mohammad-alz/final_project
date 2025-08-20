import pandas as pd
from django.core.management.base import BaseCommand
from api.models import Price, TechnicalAnalysis

class Command(BaseCommand):
    help = 'Calculates a wide range of technical analysis indicators and saves the counts.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Calculating expanded indicator counts...")
        
        prices = Price.objects.all().order_by('timestamp').values('timestamp', 'price')
        if len(prices) < 200:
            self.stdout.write(self.style.WARNING("Not enough price data for a full analysis (need at least 200 points)."))
            return

        df = pd.DataFrame(list(prices))
        df['price'] = pd.to_numeric(df['price'])
        df['high'] = df['price']
        df['low'] = df['price']
        df['close'] = df['price']
        last_price = df['close'].iloc[-1]

        # --- 1. Moving Averages ---
        ma_signals = {'buy': 0, 'sell': 0, 'neutral': 0}
        ma_periods = [10, 20, 30, 50, 100, 200]
        for period in ma_periods:
            df[f'sma{period}'] = df['close'].rolling(window=period).mean()
            df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
            ma_signals['buy' if last_price > df[f'sma{period}'].iloc[-1] else 'sell'] += 1
            ma_signals['buy' if last_price > df[f'ema{period}'].iloc[-1] else 'sell'] += 1

        # --- 2. Oscillators ---
        osc_signals = {'buy': 0, 'sell': 0, 'neutral': 0}

        # RSI (Relative Strength Index)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        if rsi.iloc[-1] > 70: osc_signals['sell'] += 1
        elif rsi.iloc[-1] < 30: osc_signals['buy'] += 1
        else: osc_signals['neutral'] += 1

        # Stochastic Oscillator
        low14 = df['low'].rolling(14).min()
        high14 = df['high'].rolling(14).max()
        k_percent = 100 * ((df['close'] - low14) / (high14 - low14))
        if k_percent.iloc[-1] > 80: osc_signals['sell'] += 1
        elif k_percent.iloc[-1] < 20: osc_signals['buy'] += 1
        else: osc_signals['neutral'] += 1
        
        # MACD (Moving Average Convergence Divergence)
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        if macd.iloc[-1] > signal_line.iloc[-1]: osc_signals['buy'] += 1
        else: osc_signals['sell'] += 1
        
        # Williams %R
        high14_w = df['high'].rolling(14).max()
        low14_w = df['low'].rolling(14).min()
        williams_r = -100 * ((high14_w - df['close']) / (high14_w - low14_w))
        if williams_r.iloc[-1] > -20: osc_signals['sell'] += 1
        elif williams_r.iloc[-1] < -80: osc_signals['buy'] += 1
        else: osc_signals['neutral'] += 1
        
        # Awesome Oscillator
        median_price = (df['high'] + df['low']) / 2
        ao = median_price.rolling(5).mean() - median_price.rolling(34).mean()
        if ao.iloc[-1] > 0 and ao.iloc[-2] < 0: # Bullish crossover
             osc_signals['buy'] += 1
        elif ao.iloc[-1] < 0 and ao.iloc[-2] > 0: # Bearish crossover
             osc_signals['sell'] += 1
        else:
             osc_signals['neutral'] += 1
        
        # --- 3. Aggregate, Determine Signal, and Save ---
        summary_buy = ma_signals['buy'] + osc_signals['buy']
        summary_sell = ma_signals['sell'] + osc_signals['sell']
        summary_neutral = ma_signals['neutral'] + osc_signals['neutral']

        final_signal = TechnicalAnalysis.Signal.NEUTRAL
        if summary_buy > summary_sell * 2: final_signal = TechnicalAnalysis.Signal.STRONG_BUY
        elif summary_sell > summary_buy * 2: final_signal = TechnicalAnalysis.Signal.STRONG_SELL
        elif summary_buy > summary_sell: final_signal = TechnicalAnalysis.Signal.BUY
        elif summary_sell > summary_buy: final_signal = TechnicalAnalysis.Signal.SELL

        TechnicalAnalysis.objects.update_or_create(
            id=1,
            defaults={
                'ma_buy_count': ma_signals['buy'], 'ma_sell_count': ma_signals['sell'], 'ma_neutral_count': ma_signals['neutral'],
                'osc_buy_count': osc_signals['buy'], 'osc_sell_count': osc_signals['sell'], 'osc_neutral_count': osc_signals['neutral'],
                'summary_buy_count': summary_buy, 'summary_sell_count': summary_sell, 'summary_neutral_count': summary_neutral,
                'summary_signal': final_signal,
            }
        )
        self.stdout.write(self.style.SUCCESS(f"Successfully saved full analysis. Final signal: {final_signal}"))