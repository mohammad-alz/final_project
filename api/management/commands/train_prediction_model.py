# api/management/commands/train_prediction_model.py
import pandas as pd
import pandas_ta as ta
import joblib
import numpy as np
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from sklearn.ensemble import RandomForestClassifier
from api.models import Price, PricePrediction

def train_and_save_model(horizon_name, X, y):
    """
    Helper function to train, predict, and save a model for a specific horizon.
    """
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    model.fit(X, y)
    
    last_features = X.iloc[[-1]]
    prediction_class = model.predict(last_features)[0]
    prediction_proba = model.predict_proba(last_features)[0]

    signal_map = {1: 'BUY', -1: 'SELL', 0: 'HOLD'}
    final_signal = signal_map[prediction_class]
    confidence = prediction_proba.max() * 100

    model_file = ContentFile(joblib.dump(model, f'{horizon_name}_model.joblib')[0])
    pred_obj, _ = PricePrediction.objects.update_or_create(
        horizon=horizon_name,
        defaults={
            'signal': final_signal,
            'confidence': confidence,
            'model_accuracy': model.score(X, y)
        }
    )
    pred_obj.model_file.save(f'{horizon_name}_model.joblib', model_file, save=True)
    return f"{horizon_name} model saved. Signal: {final_signal} ({confidence:.2f}%)"

class Command(BaseCommand):
    help = 'Trains classification models for daily and weekly signals.'

    def handle(self, *args, **kwargs):
        prices = Price.objects.all().order_by('timestamp').values('timestamp', 'price')
        if len(prices) < 200:
            self.stdout.write(self.style.WARNING("Not enough data."))
            return

        df = pd.DataFrame(list(prices))
        df.set_index(pd.to_datetime(df['timestamp']), inplace=True)
        df.rename(columns={'price': 'close'}, inplace=True)

        df.ta.sma(length=20, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        
        def get_target(change, threshold=0.01):
            if change > threshold: return 1 # Buy
            elif change < -threshold: return -1 # Sell
            else: return 0 # Hold

        df['price_change_1d'] = (df['close'].shift(-1) - df['close']) / df['close']
        df['target_daily'] = df['price_change_1d'].apply(get_target)
        
        df['price_change_7d'] = (df['close'].shift(-7) - df['close']) / df['close']
        df['target_weekly'] = df['price_change_7d'].apply(get_target)
        
        df.dropna(inplace=True)
        features = [col for col in df.columns if col.startswith(('SMA', 'EMA', 'RSI', 'MACD'))]
        X = df[features]

        y_daily = df['target_daily']
        daily_result = train_and_save_model(PricePrediction.Horizon.DAILY, X, y_daily)
        self.stdout.write(self.style.SUCCESS(daily_result))

        y_weekly = df['target_weekly']
        weekly_result = train_and_save_model(PricePrediction.Horizon.WEEKLY, X, y_weekly)
        self.stdout.write(self.style.SUCCESS(weekly_result))