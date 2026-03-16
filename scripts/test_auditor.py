import asyncio
import pandas as pd
import numpy as np
from app.services.ml_engine import MarketAnalyzer
from app.services.ai_auditor import AIAuditor
from app.utils.regime_detector import MarketRegime

async def test_auditor_logic():
    print("--- Starting AI Auditor Verification ---")
    
    # 1. Setup Mock Data
    # Create a scenario where Scalp and Momentum conflict
    data = {
        'Close': [100.0] * 51,
        'High': [101.0] * 51,
        'Low': [99.0] * 51,
        'Volume': [1000] * 51,
        'ATR': [1.0] * 51,
        'RSI': [20.0] * 51, # Bullish Scalp (Oversold)
        'MACD': [0.1] * 51,
        'Signal_Line': [0.05] * 51,
        'SMA_200': [110.0] * 51, # Price < SMA_200 -> Bear Trend
    }
    df = pd.DataFrame(data)
    
    # Manually set signals to force conflict
    df['Scalp_Signal'] = 2  # Bullish
    df['Momentum_Signal'] = -2 # Bearish
    df['MR_Signal'] = 0
    
    analyzer = MarketAnalyzer("TEST")
    analyzer.signals = df
    
    raw_prediction = {
        "symbol": "TEST",
        "prediction": "BULLISH",
        "confidence": 0.8,
        "regime": MarketRegime.BEAR_TREND.value # Conflict with prediction
    }
    
    auditor = AIAuditor()
    print("Running verification for 'High Friction' + 'Negative Regime Alignment'...")
    audited_result = auditor.verify_prediction(raw_prediction, df)
    
    print(f"Prediction: {audited_result['prediction']}")
    print(f"Raw Confidence: {raw_prediction['confidence']}")
    print(f"Adjusted Confidence: {audited_result['adjusted_confidence']}")
    print(f"Status: {audited_result['verification_status']}")
    print("\nAuditor Logs:")
    for log in audited_result['auditor_logs']:
        print(f" - {log}")
        
    print(f"\nReasoning Path:\n{audited_result['reasoning_path']}")
    
    # Assertions
    assert audited_result['adjusted_confidence'] < raw_prediction['confidence'], "Confidence should be reduced"
    assert "conflicts with the macro" in audited_result['reasoning_path'], "Alignment issue should be noted"
    assert any("Negative Regime Alignment" in log for log in audited_result['auditor_logs']), "Log should contain alignment warning"
    
    print("\n--- Verification Passed! ---")

if __name__ == "__main__":
    asyncio.run(test_auditor_logic())
