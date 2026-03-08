import pandas as pd
import numpy as np
from app.core import config
from ml_engine import MarketAnalyzer
from regime_detector import RegimeDetector, MarketRegime
import logging

logger = logging.getLogger(__name__)

class VectorizedBacktester:
    """
    Advanced Backtesting Engine with vectorized performance metrics.
    Decoupled from live prediction streams.
    """
    def __init__(self, symbol, initial_capital=100000.0, commission=0.0, slippage=0.0001):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.analyzer = MarketAnalyzer(symbol)
        self.regime_detector = RegimeDetector()

    async def run(self, period="1y", interval="1d"):
        """Main execution loop for backtesting."""
        # 1. Fetch historical bulk data (Separated from live via analyzer)
        await self.analyzer.fetch_data(period=period, interval=interval)
        self.analyzer.calculate_indicators()
        
        # 2. Generate signals for the entire history (Vectorized)
        df = self.analyzer.generate_vectorized_signals()
        
        # 3. Apply Regime Detection to weights (Vectorized if possible, or iterative bucketed)
        # For simplicity, we'll calculate regime daily if interval is intraday
        # or use a rolling regime for the whole df
        df['Regime'] = df.apply(lambda x: self.regime_detector.detect_regime(df.loc[:x.name].tail(100)), axis=1)
        
        # Apply weighting logic based on regime
        def calc_composite_score(row):
            weights = self.regime_detector.get_strategy_weights(row['Regime'])
            return (
                (row['Scalp_Signal'] * weights['scalping']) +
                (row['Momentum_Signal'] * weights['momentum']) +
                (row['MR_Signal'] * weights['mean_reversion'])
            )
            
        df['Composite_Score'] = df.apply(calc_composite_score, axis=1)
        
        # 4. Generate Position (Shifted to avoid lookahead bias)
        df['Signal'] = 0
        df.loc[df['Composite_Score'] >= 1.0, 'Signal'] = 1
        df.loc[df['Composite_Score'] <= -1.0, 'Signal'] = -1
        
        df['Position'] = df['Signal'].shift(1).fillna(0)
        
        # 5. Returns Calculation (Vectorized)
        df['Market_Return'] = df['Close'].pct_change()
        # Apply slippage and commission to entries/exits
        df['Execution_Cost'] = (df['Position'].diff().abs() * (self.slippage + self.commission))
        
        df['Strategy_Return'] = (df['Position'] * df['Market_Return']) - df['Execution_Cost']
        df['Equity_Curve'] = self.initial_capital * (1 + df['Strategy_Return']).cumprod()
        
        return self._calculate_metrics(df)

    def _calculate_metrics(self, df: pd.DataFrame) -> dict:
        """Computes institutional-grade trading metrics."""
        returns = df['Strategy_Return'].dropna()
        
        total_return = (df['Equity_Curve'].iloc[-1] / self.initial_capital) - 1
        
        # Annualized volatility (assuming 252 trading days)
        # Adjust scale based on interval (simplified to daily for now)
        vol = returns.std() * np.sqrt(252)
        
        # Sharpe Ratio
        risk_free_rate = 0.02 # Assume 2%
        sharpe = (returns.mean() * 252 - risk_free_rate) / vol if vol > 0 else 0
        
        # Sortino Ratio (downside risk only)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino = (returns.mean() * 252 - risk_free_rate) / downside_std if downside_std > 0 else 0
        
        # Max Drawdown
        rolling_max = df['Equity_Curve'].cummax()
        drawdown = df['Equity_Curve'] / rolling_max - 1
        max_dd = drawdown.min()
        
        # Profit Factor
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Win Rate
        win_rate = len(returns[returns > 0]) / len(returns[returns != 0]) if len(returns[returns != 0]) > 0 else 0
        
        return {
            "symbol": self.symbol,
            "total_return": round(total_return * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "max_drawdown": round(max_dd * 100, 2),
            "profit_factor": round(profit_factor, 2),
            "win_rate": round(win_rate * 100, 2),
            "final_equity": round(df['Equity_Curve'].iloc[-1], 2),
            "equity_curve": df['Equity_Curve'].tolist()
        }
