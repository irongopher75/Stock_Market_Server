import pandas as pd
import numpy as np
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    HIGH_VOL_RANGING = "HIGH_VOL_RANGING"
    LOW_VOL_RANGING = "LOW_VOL_RANGING"
    NEUTRAL = "NEUTRAL"

class RegimeDetector:
    """
    Classifies market state based on ADX and Volatility.
    """
    def __init__(self, adx_threshold: float = 25.0):
        self.adx_threshold = adx_threshold

    def detect_regime(self, df: pd.DataFrame) -> MarketRegime:
        if df.empty or len(df) < 50:
            return MarketRegime.NEUTRAL
            
        last_row = df.iloc[-1]
        
        # 1. Trend Strength (using simple SMA distance as proxy for now if ADX not pre-calc)
        # In a full implementation, we'd use a proper ADX
        close = last_row['Close']
        sma_200 = last_row.get('SMA_200', close)
        
        # Use ATR/Price for relative volatility
        volatility = (last_row.get('ATR', 0) / close) * 100
        vol_median = (df['ATR'] / df['Close']).median() * 100
        
        is_trending = abs(close - sma_200) / sma_200 > 0.02 # 2% deviation from SMA 200
        
        if is_trending:
            if close > sma_200:
                return MarketRegime.BULL_TREND
            else:
                return MarketRegime.BEAR_TREND
        else:
            if volatility > vol_median * 1.2:
                return MarketRegime.HIGH_VOL_RANGING
            else:
                return MarketRegime.LOW_VOL_RANGING

    def get_strategy_weights(self, regime: MarketRegime) -> dict:
        """
        Returns optimized weights for strategy ensemble based on regime.
        """
        weights = {
            MarketRegime.BULL_TREND: {
                "scalping": 0.2, "momentum": 0.6, "mean_reversion": 0.2
            },
            MarketRegime.BEAR_TREND: {
                "scalping": 0.2, "momentum": 0.5, "mean_reversion": 0.3
            },
            MarketRegime.HIGH_VOL_RANGING: {
                "scalping": 0.5, "momentum": 0.1, "mean_reversion": 0.4
            },
            MarketRegime.LOW_VOL_RANGING: {
                "scalping": 0.3, "momentum": 0.2, "mean_reversion": 0.5
            },
            MarketRegime.NEUTRAL: {
                "scalping": 0.33, "momentum": 0.33, "mean_reversion": 0.34
            }
        }
        return weights.get(regime, weights[MarketRegime.NEUTRAL])
