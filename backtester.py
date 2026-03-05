import pandas as pd
import numpy as np
import config
from ml_engine import MarketAnalyzer

class Backtester:
    """
    A foundational backtesting framework to validate ML Engine strategies
    using historically unseen data (Out-Of-Sample validation).
    """
    def __init__(self, symbol, initial_capital=100000.0, period="1y", interval="1d"):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.period = period
        self.interval = interval
        self.analyzer = MarketAnalyzer(symbol)
        
    def run_backtest(self):
        # Fetch data and compute all indicators for the full period
        self.analyzer.fetch_data(period=self.period, interval=self.interval)
        self.analyzer.calculate_indicators()
        
        df = self.analyzer.data.copy()
        
        # We need a rolling average volume & high for Momentum logic
        df['Avg_Volume'] = df['Volume'].rolling(window=config.MOMENTUM_LOOKBACK).mean()
        df['Recent_High'] = df['High'].rolling(window=config.MOMENTUM_LOOKBACK).max()
        
        # Replicate the ML Engine's composite scoring logic over history
        signals = []
        total_scores = []
        for i in range(len(df)):
            if i < config.SMA_SLOW: # Not enough data for 200 SMA
                signals.append(0) 
                total_scores.append(0.0)
                continue
                
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            score = 0
            scalp_score = 0
            
            # Scalping component
            if row['RSI'] < 30: scalp_score += 2
            elif row['RSI'] > 70: scalp_score -= 2
            
            if row['MACD'] > row['Signal_Line'] and prev_row['MACD'] <= prev_row['Signal_Line']: scalp_score += 2
            elif row['MACD'] < row['Signal_Line'] and prev_row['MACD'] >= prev_row['Signal_Line']: scalp_score -= 2
            
            if row['Volume'] > row['Avg_Volume'] * config.VOL_确认_RATIO:
                scalp_score *= 1.5
                
            # Momentum component
            if row['Close'] > row['Recent_High'] * config.MOMENTUM_PROXIMITY:
                if row['Volume'] > row['Avg_Volume'] * 1.3:
                    score += 2
                    
            # Mean Reversion component
            if row['Close'] < row['BB_Lower'] and row['RSI'] < 35:
                score += 2
            elif row['Close'] > row['BB_Upper'] and row['RSI'] > 65:
                score -= 2
                
            total_score = score + (scalp_score * 0.5)
            total_scores.append(total_score)
            
            # Generate actionable signal
            if total_score >= config.BULLISH_SCORE_THRESHOLD:
                signals.append(1) # Long
            elif total_score <= config.BEARISH_SCORE_THRESHOLD:
                signals.append(-1) # Short
            else:
                signals.append(0) # Neutral
                
        df['Signal'] = signals
        df['Composite_Score'] = total_scores
        
        # Shift signal by 1 so we trade on the NEXT candle to avoid look-ahead bias
        df['Position'] = df['Signal'].shift(1).fillna(0)
        
        # Calculate Returns (close-to-close)
        df['Market_Return'] = df['Close'].pct_change()
        
        # Strategy Return = Position * Market Return
        df['Strategy_Return'] = df['Position'] * df['Market_Return']
        
        # Equity Curve
        df['Equity'] = self.initial_capital * (1 + df['Strategy_Return']).cumprod()
        
        # Metrics calculation
        total_return = (df['Equity'].iloc[-1] / self.initial_capital) - 1
        
        rolling_max = df['Equity'].cummax()
        drawdown = df['Equity'] / rolling_max - 1
        max_drawdown = drawdown.min()
        
        winning_trades = len(df[df['Strategy_Return'] > 0])
        total_active_intervals = len(df[df['Strategy_Return'] != 0])
        win_rate = winning_trades / total_active_intervals if total_active_intervals > 0 else 0
        
        # Diagnostics
        valid_scores = df['Composite_Score'][config.SMA_SLOW:]
        
        return {
            "symbol": self.symbol,
            "period": self.period,
            "initial_capital": self.initial_capital,
            "final_equity": round(df['Equity'].iloc[-1], 2),
            "total_return_pct": round(total_return * 100, 2),
            "max_drawdown_pct": round(max_drawdown * 100, 2),
            "win_rate_pct": round(win_rate * 100, 2),
            "total_intervals_in_market": total_active_intervals,
            "score_diagnostics": valid_scores.describe().to_dict(),
            "bullish_threshold": config.BULLISH_SCORE_THRESHOLD,
            "bearish_threshold": config.BEARISH_SCORE_THRESHOLD,
            "weights": {"Momentum": 2, "Mean Reversion": 2, "Scalping": 0.5 * 2, "Volume/Trend": 1}
        }

if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"
    print(f"Running backtest for {symbol}...")
    tester = Backtester(symbol, period="1y", interval="1d")
    results = tester.run_backtest()
    print("-" * 30)
    for k, v in results.items():
        print(f"{k}: {v}")
    print("-" * 30)
