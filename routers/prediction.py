from fastapi import APIRouter, Depends, HTTPException
import models, schemas, auth
from ml_engine import MarketAnalyzer
from risk_engine import RiskEngine
import logging
import re
from typing import List

router = APIRouter(prefix="/predict", tags=["prediction"])

logger = logging.getLogger(__name__)

@router.get("/{symbol}")
async def get_prediction(
    symbol: str, 
    interval: str = "1h",
    period: str = "1mo",
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # 1. Validate Symbol
    if not re.match(r"^[A-Z0-9.-]{1,20}$", symbol.upper()):
        raise HTTPException(status_code=400, detail="Invalid stock symbol format.")
        
    try:
        analyzer = MarketAnalyzer(symbol)
        analyzer.fetch_data(period=period, interval=interval)
        result = analyzer.predict_direction()
        
        # Log to DB
        log_entry = models.PredictionLog(
            symbol=symbol,
            current_price=result['current_price'],
            predicted_direction=result['prediction'],
            confidence_score=result['confidence'],
            suggested_strategy=result['strategy'],
            user_id=str(current_user.id)
        )
        await log_entry.insert()
        
        # Add Payoff Graph Data if strategy is clear
        payoff_data = []
        if "CE" in result['strategy']:
            strike = round(result['current_price'] / 50) * 50
            payoff_data = analyzer.generate_payoff_graph("CE", strike, 100)
            result['strike'] = strike
            result['option_type'] = "CE"
        elif "PE" in result['strategy']:
            strike = round(result['current_price'] / 50) * 50
            payoff_data = analyzer.generate_payoff_graph("PE", strike, 100)
            result['strike'] = strike
            result['option_type'] = "PE"
            
        result['payoff_graph'] = payoff_data
        
        # --- HFT Algo 5.1/5.2: Risk Management Integration ---
        # Using a dummy starting capital of $10,000 for calculation
        risk_engine = RiskEngine(account_balance=10000)
        atr = analyzer.data['ATR'].iloc[-1]
        
        # Calculate risk based on direction
        side = "BUY" if result['prediction'] == "BULLISH" else "SELL"
        risk_details = risk_engine.get_position_details(
            entry_price=result['current_price'],
            atr=atr,
            confidence=result['confidence'],
            side=side
        )
        
        result['hft_risk'] = risk_details
        # -----------------------------------------------------
        
        return result
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Prediction error for {symbol}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Prediction failed. Please try again later.")

@router.get("/history/me", response_model=List[models.PredictionLog])
async def get_my_history(
    current_user: models.User = Depends(auth.get_current_active_user)
):
    return await models.PredictionLog.find(models.PredictionLog.user_id == str(current_user.id)).sort("-timestamp").limit(10).to_list()

@router.get("/history/all", response_model=List[models.PredictionLog])
async def get_history(
    current_user: models.User = Depends(auth.get_current_admin)
):
    return await models.PredictionLog.find().sort("-timestamp").limit(50).to_list()
