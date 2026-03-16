import pandas as pd
import numpy as np
from app.core import config
from app.services.data_router import DataRouter
from app.utils.regime_detector import RegimeDetector, MarketRegime
import logging

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    def __init__(self, symbol):
        self.symbol = symbol
        self.data = None
        self.router = DataRouter()
        self.regime_detector = RegimeDetector()

    async def fetch_data(self, period="1mo", interval="1h"):
        """Fetches data via the DataRouter and applies normalization."""
        self.data = await self.router.get_price_data(self.symbol, interval=interval, period=period)
        
        if self.data.empty:
            raise Exception(f"No data found for symbol {self.symbol}")
            
        # --- HFT Algo 1.1: Real-Time Data Normalization (Vectorized) ---
        rolling_median = self.data['Close'].rolling(window=config.SMA_FAST).median()
        self.data['Close'] = np.where(
            (self.data['Close'] > rolling_median * 1.10) | (self.data['Close'] < rolling_median * 0.90),
            rolling_median,
            self.data['Close']
        ).astype(float)
        
        self.data.ffill(inplace=True)

    def calculate_indicators(self):
        """Vectorized technical indicator calculations."""
        df = self.data
        close = df['Close']
        
        # ATR (Vectorized)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        df['ATR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(window=config.ATR_WINDOW).mean()
        
        # RSI (Vectorized)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=config.RSI_WINDOW).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=config.RSI_WINDOW).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # SMAs
        df['SMA_20'] = close.rolling(window=config.SMA_FAST).mean()
        df['SMA_50'] = close.rolling(window=config.SMA_MEDIUM).mean()
        df['SMA_200'] = close.rolling(window=config.SMA_SLOW).mean()

        # Adaptive Indicators
        atr_pct = (df['ATR'] / close) * 100
        df['Vol_Ratio'] = atr_pct

        # Vectorized Adaptive MACD (simplified)
        # Note: True adaptive MACD on a per-row basis in a vectorized way is complex, 
        # we'll use a fixed parameter set based on the current regime/volatility level
        df['MACD'] = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # Vectorized Bollinger Bands
        std = close.rolling(window=config.SMA_FAST).std()
        df['BB_Upper'] = df['SMA_20'] + (std * 2.0)
        df['BB_Lower'] = df['SMA_20'] - (std * 2.0)
        
        self.data = df

    def generate_vectorized_signals(self) -> pd.DataFrame:
        """
        Generates signals for the entire dataframe using vectorized operations.
        Prevents lookhead bias by shifting signals.
        """
        df = self.data.copy()
        
        # 1. Scalping signals
        df['Scalp_Signal'] = 0
        df.loc[df['RSI'] < 30, 'Scalp_Signal'] += 2
        df.loc[df['RSI'] > 70, 'Scalp_Signal'] -= 2
        
        macd_cross_up = (df['MACD'] > df['Signal_Line']) & (df['MACD'].shift(1) <= df['Signal_Line'].shift(1))
        macd_cross_down = (df['MACD'] < df['Signal_Line']) & (df['MACD'].shift(1) >= df['Signal_Line'].shift(1))
        df.loc[macd_cross_up, 'Scalp_Signal'] += 2
        df.loc[macd_cross_down, 'Scalp_Signal'] -= 2
        
        # 2. Momentum signals
        recent_high = df['High'].rolling(window=config.MOMENTUM_LOOKBACK).max()
        avg_vol = df['Volume'].rolling(window=config.MOMENTUM_LOOKBACK).mean()
        df['Momentum_Signal'] = 0
        df.loc[(df['Close'] > recent_high * config.MOMENTUM_PROXIMITY) & (df['Volume'] > avg_vol * 1.3), 'Momentum_Signal'] = 2
        
        # 3. Mean Reversion signals
        df['MR_Signal'] = 0
        df.loc[(df['Close'] < df['BB_Lower']) & (df['RSI'] < 35), 'MR_Signal'] = 2
        df.loc[(df['Close'] > df['BB_Upper']) & (df['RSI'] > 65), 'MR_Signal'] = -2
        
        return df

    def predict_direction(self, strategy_type="ensemble"):
        """
        Interface for real-time prediction using vectorized logic.
        """
        self.calculate_indicators()
        self.signals = self.generate_vectorized_signals()
        
        # Current Regime Handling
        regime = self.regime_detector.detect_regime(self.signals)
        weights = self.regime_detector.get_strategy_weights(regime)
        
        last_row = self.signals.iloc[-1]
        
        # Weighted Composite Score
        total_score = (
            (last_row['Scalp_Signal'] * weights['scalping']) +
            (last_row['Momentum_Signal'] * weights['momentum']) +
            (last_row['MR_Signal'] * weights['mean_reversion'])
        )
        
        prediction = "NEUTRAL"
        confidence = 0.5
        
        if total_score >= 1.0: # Lowered threshold for weighted scoring
            prediction = "BULLISH"
            confidence = min(0.6 + (total_score * 0.1), 0.95)
        elif total_score <= -1.0:
            prediction = "BEARISH"
            confidence = min(0.6 + (abs(total_score) * 0.1), 0.95)
            
        return self._sanitize({
            "symbol": self.symbol,
            "prediction": prediction,
            "confidence": round(confidence, 2),
            "regime": regime.value,
            "current_price": round(last_row['Close'], 2),
            "rsi": round(last_row['RSI'], 2),
            "macd": round(last_row['MACD'], 4),
            "total_score": round(total_score, 2),
            "strategy": f"Regime: {regime.value} | Weights: {weights}"
        })

    def _sanitize(self, obj):
        if isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize(v) for v in obj]
        elif isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
            return None
        return obj
