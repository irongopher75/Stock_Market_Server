import numpy as np
import config

class RiskEngine:
    def __init__(
        self, 
        account_balance=config.INITIAL_BALANCE, 
        win_rate=config.DEFAULT_WIN_RATE, 
        avg_win=config.DEFAULT_AVG_WIN, 
        avg_loss=config.DEFAULT_AVG_LOSS
    ):
        self.account_balance = account_balance
        self.win_rate = win_rate
        self.avg_win = avg_win
        self.avg_loss = avg_loss

    def calculate_kelly_size(self, confidence=1.0):
        """
        HFT Algo 5.1: Kelly Criterion
        f* = (bp - q) / b
        """
        b = self.avg_win / self.avg_loss
        p = self.win_rate
        q = 1 - p
        
        kelly_f = (b * p - q) / b
        
        # Apply fractional Kelly (0.25) for safety and scale by confidence
        safe_f = max(0, kelly_f * 0.25 * confidence)
        
        # Cap at 15% of account
        return min(safe_f, 0.15)

    def calculate_dynamic_stops(self, entry_price, atr, side="BUY", volatility_ratio=1.0):
        """
        HFT Algo 5.2: Dynamic Stop Loss with Hard Floor Constraints
        """
        # Hard floor for minimum stop distance to avoid noise-outs in low vol
        MIN_STOP_PCT = 0.005 # 0.5% minimum stop distance
        
        # Adjust multiplier based on volatility
        multiplier = 2.0
        if volatility_ratio > 1.5:
            multiplier = 2.5
        elif volatility_ratio < 0.7:
            multiplier = 1.5
            
        calculated_stop_dist = atr * multiplier
        min_stop_dist = entry_price * MIN_STOP_PCT
        
        # Apply the absolute floor to stop distance
        effective_stop_dist = max(calculated_stop_dist, min_stop_dist)
            
        if side == "BUY":
            stop_loss = entry_price - effective_stop_dist
            take_profit = entry_price + (effective_stop_dist * 1.5)
        else:
            stop_loss = entry_price + effective_stop_dist
            take_profit = entry_price - (effective_stop_dist * 1.5)
            
        return {
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2)
        }

    def get_position_details(self, entry_price, atr, confidence=0.7, side="BUY"):
        size_fraction = self.calculate_kelly_size(confidence)
        risk_amount = self.account_balance * size_fraction
        
        stops = self.calculate_dynamic_stops(entry_price, atr, side)
        
        # Calculate quantity based on risk amount and stop distance
        stop_dist = abs(entry_price - stops["stop_loss"])
        if stop_dist > 0:
            qty = int(risk_amount / stop_dist)
        else:
            qty = 0
            
        return {
            "quantity": qty,
            "risk_amount": round(risk_amount, 2),
            **stops
        }
        
    def check_circuit_breakers(self, current_day_pnl: float, open_exposure: float) -> bool:
        """
        Portfolio-level risk circuit breaker.
        Returns True if trading is ALLOWED, False if HALTED.
        """
        MAX_DAILY_DRAWDOWN_PCT = -0.03 # Stop trading at 3% daily loss
        MAX_EXPOSURE_PCT = 0.50 # Max 50% of balance exposed
        
        # Check Daily Drawdown limit
        current_drawdown_pct = current_day_pnl / self.account_balance
        if current_drawdown_pct <= MAX_DAILY_DRAWDOWN_PCT:
            return False # Halt trading, hard stop hit
            
        # Check Max Exposure limit
        if (open_exposure / self.account_balance) >= MAX_EXPOSURE_PCT:
            return False # Wait for positions to close
            
        return True
