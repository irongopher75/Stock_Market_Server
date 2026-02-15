from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, database, auth
from ..ml_engine import MarketAnalyzer
import json

router = APIRouter(prefix="/predict", tags=["prediction"])

import re
import logging

# Configure logger
logger = logging.getLogger(__name__)

@router.get("/{symbol}")
def get_prediction(
    symbol: str, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # 1. Validate Symbol
    # Allow alphanumeric, dot (for .NS), and dash, length 1-20
    if not re.match(r"^[A-Z0-9.-]{1,20}$", symbol.upper()):
        raise HTTPException(status_code=400, detail="Invalid stock symbol format.")
    try:
        analyzer = MarketAnalyzer(symbol)
        analyzer.fetch_data()
        result = analyzer.predict_direction()
        
        # Log to DB
        log_entry = models.PredictionLog(
            symbol=symbol,
            current_price=result['current_price'],
            predicted_direction=result['prediction'],
            confidence_score=result['confidence'],
            suggested_strategy=result['strategy'],
            user_id=current_user.id
        )
        db.add(log_entry)
        db.commit()
        
        # Add Payoff Graph Data if strategy is clear
        payoff_data = []
        if "CE" in result['strategy']:
            # Mock Strike Price selection (ATM)
            strike = round(result['current_price'] / 50) * 50
            payoff_data = analyzer.generate_payoff_graph("CE", strike, 100) # Assumed premium 100
            result['strike'] = strike
            result['option_type'] = "CE"
        elif "PE" in result['strategy']:
            strike = round(result['current_price'] / 50) * 50
            payoff_data = analyzer.generate_payoff_graph("PE", strike, 100)
            result['strike'] = strike
            result['option_type'] = "PE"
            
        result['payoff_graph'] = payoff_data
        
        return result
        
    except HTTPException as he:
        # Re-raise HTTP exceptions (like 400s) as is
        raise he
    except Exception as e:
        # 2. Sanitize Error
        logger.error(f"Prediction error for {symbol}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Prediction failed. Please try again later.")

@router.get("/history/me")
def get_my_history(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    return db.query(models.PredictionLog).filter(models.PredictionLog.user_id == current_user.id).order_by(models.PredictionLog.timestamp.desc()).limit(10).all()

@router.get("/history/all")
def get_history(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    return db.query(models.PredictionLog).order_by(models.PredictionLog.timestamp.desc()).limit(50).all()
