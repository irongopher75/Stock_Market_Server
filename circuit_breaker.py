import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, max_daily_loss_pct=0.03, max_drawdown_pct=0.15):
        self.is_triggered = False
        self.trigger_reason = None
        self.trigger_time = None
        
        # Risk Limits
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        
        # State
        self.daily_pnl = 0.0
        self.peak_equity = 0.0
        self.current_equity = 0.0
        self.consecutive_losses = 0
        
    def update_pnl(self, pnl, current_equity):
        self.daily_pnl += pnl
        self.current_equity = current_equity
        self.peak_equity = max(self.peak_equity, current_equity)
        
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
            
        self._check_triggers()
        
    def _check_triggers(self):
        """
        HFT Algo 11.2: Check all circuit breaker conditions
        """
        if self.is_triggered:
            return

        # 1. Daily Loss Limit
        daily_loss_pct = (self.daily_pnl / self.peak_equity) if self.peak_equity > 0 else 0
        if daily_loss_pct < -self.max_daily_loss_pct:
            self.trigger("Daily Loss Limit Hit (-{:.2%})".format(abs(daily_loss_pct)))
            
        # 2. Max Drawdown
        drawdown_pct = (self.current_equity - self.peak_equity) / self.peak_equity if self.peak_equity > 0 else 0
        if drawdown_pct < -self.max_drawdown_pct:
            self.trigger("Max Drawdown Limit Hit (-{:.2%})".format(abs(drawdown_pct)))
            
        # 3. Consecutive Losses (Error check)
        if self.consecutive_losses >= 10:
            self.trigger("Too many consecutive losses (10)")

    def trigger(self, reason):
        self.is_triggered = True
        self.trigger_reason = reason
        self.trigger_time = datetime.now()
        logger.critical(f"CIRCUIT BREAKER TRIGGERED: {reason}")
        # In a real system, this would send alerts and cancel all orders
        
    def reset(self):
        # Requires manual intervention or start of new day
        self.is_triggered = False
        self.trigger_reason = None
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        logger.info("Circuit Breaker Reset")
