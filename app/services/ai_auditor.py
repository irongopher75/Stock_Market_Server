import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, List
from app.utils.regime_detector import MarketRegime

logger = logging.getLogger(__name__)

class AIAuditor:
    """
    The 'Cognitive Layer' that provides awareness and verification 
    to the probabilistic ML engine.
    """
    
    def __init__(self):
        self.audit_log = []

    def log(self, message: str):
        self.audit_log.append(message)
        logger.info(f"[AI Auditor] {message}")

    def verify_prediction(self, raw_prediction: Dict[str, Any], signal_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Applies mathematical checks to the raw ML output.
        - Entropy Check (Signal Variance)
        - Bayesian Adjustment (Regime Alignment)
        - Reasoning Generation
        """
        self.audit_log = []
        self.log(f"Initializing audit for symbol {raw_prediction.get('symbol', 'Unknown')}")
        
        last_row = signal_df.iloc[-1]
        
        # 1. Entropy Check: Measuring 'Predictive Friction'
        # We look at the disagreement between different atomic logic units
        signals = [
            last_row.get('Scalp_Signal', 0),
            last_row.get('Momentum_Signal', 0),
            last_row.get('MR_Signal', 0)
        ]
        
        # Calculate variance as a proxy for entropy/uncertainty
        variance = np.var(signals)
        friction_factor = 1.0
        
        if variance > 1.5: # Signals are pointing in very different directions
            friction_factor = 0.7
            self.log(f"High Predictive Friction detected (variance: {round(variance, 2)}). Different indicators are conflicting.")
        elif variance < 0.5:
            friction_factor = 1.1
            self.log("Low Friction: Indicators are in high alignment.")

        # 2. Bayesian-style Regime Adjustment
        regime = raw_prediction.get("regime")
        prediction = raw_prediction.get("prediction")
        confidence = raw_prediction.get("confidence", 0.5)
        
        regime_alignment = 1.0
        if prediction == "BULLISH":
            if regime == MarketRegime.BULL_TREND.value:
                regime_alignment = 1.1 # Reinforce
                self.log("Positive Regime Alignment: Long bias confirmed by Bull Trend.")
            elif regime == MarketRegime.BEAR_TREND.value:
                regime_alignment = 0.6 # High skepticism
                self.log("Negative Regime Alignment: Attempting to go Long in a Bear Trend. Raising skepticism.")
        elif prediction == "BEARISH":
            if regime == MarketRegime.BEAR_TREND.value:
                regime_alignment = 1.1
                self.log("Positive Regime Alignment: Short bias confirmed by Bear Trend.")
            elif regime == MarketRegime.BULL_TREND.value:
                regime_alignment = 0.6
                self.log("Negative Regime Alignment: Attempting to go Short in a Bull Trend. Raising skepticism.")

        # 3. Final Calibration
        adjusted_confidence = min(0.99, confidence * friction_factor * regime_alignment)
        
        # 4. Generate Reasoning Path
        reasoning = self._generate_reasoning(raw_prediction, friction_factor, regime_alignment)
        
        return {
            **raw_prediction,
            "adjusted_confidence": round(adjusted_confidence, 2),
            "auditor_logs": self.audit_log,
            "reasoning_path": reasoning,
            "verification_status": "VERIFIED" if adjusted_confidence >= 0.6 else "SKEPTICAL"
        }

    def _generate_reasoning(self, raw: Dict[str, Any], friction: float, alignment: float) -> str:
        path = f"The AI analyzed {raw.get('symbol')} data. "
        
        if friction < 1.0:
            path += "It noted internal conflict between scalp and momentum signals, indicating a non-binary market state. "
        else:
            path += "Indicators showed structural convergence, increasing reliability. "
            
        if alignment < 1.0:
            path += f"However, the target direction conflicts with the macro {raw.get('regime')} regime. "
        else:
            path += f"The direction is perfectly aligned with the {raw.get('regime')} context. "
            
        path += f"Final awareness score adjusted to {round(raw.get('confidence', 0) * friction * alignment, 2)}."
        return path
