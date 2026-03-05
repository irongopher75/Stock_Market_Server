from fastapi import APIRouter, Depends, HTTPException
import models, schemas, auth
from ml_engine import MarketAnalyzer
from risk_engine import RiskEngine
import logging
import re
import json
import os
import config
import asyncio
from typing import List, Dict
from datetime import datetime, timedelta, timezone
from trading_manager import TradingManager

router = APIRouter(prefix="/predict", tags=["prediction"])
trading_mgr = TradingManager()

logger = logging.getLogger(__name__)

# Path to symbol data
SYMBOL_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "nse_symbols.json")

# --- CONCURRENCY LOCKS ---
# Prevents race conditions where parallel requests bypass deduplication
# Key: (user_id, symbol)
symbol_locks: Dict[tuple, asyncio.Lock] = {}

@router.get("/symbols/{exchange}")
async def get_exchange_symbols(exchange: str):
    """Returns a list of top symbols for the requested exchange."""
    exchange = exchange.lower()
    
    # Map valid exchanges to their data files
    exchange_files = {
        "nse": "nse_symbols.json",
        "bse": "bse_symbols.json",
        "us": "us_symbols.json",
        "japan": "japan_symbols.json"
    }
    
    if exchange not in exchange_files:
        raise HTTPException(status_code=404, detail="Exchange not supported")
        
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", exchange_files[exchange])
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading symbols for {exchange}: {e}")
        return []

@router.get("/{symbol}")
async def get_prediction(
    symbol: str, 
    interval: str = "1h",
    period: str = "1mo",
    current_user: models.User = Depends(auth.get_current_active_user)
):
    symbol = symbol.upper()
    # 1. Validate Symbol
    if not re.match(r"^[A-Z0-9.-]{1,20}$", symbol):
        raise HTTPException(status_code=400, detail="Invalid stock symbol format.")
    
    # Get or create lock for this specific user/symbol pair
    lock_key = (str(current_user.id), symbol)
    if lock_key not in symbol_locks:
        symbol_locks[lock_key] = asyncio.Lock()
        
    async with symbol_locks[lock_key]:
        try:
            analyzer = MarketAnalyzer(symbol)
            await analyzer.fetch_data(period=period, interval=interval)
            result = analyzer.predict_direction()
            
            # --- DEDUPLICATION LOGIC ---
            # Use configured deduplication window
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=config.DEDUPLICATION_WINDOW_MINS)
            existing_log = await models.PredictionLog.find_one(
                models.PredictionLog.user_id == str(current_user.id),
                models.PredictionLog.symbol == symbol,
                models.PredictionLog.timestamp > cutoff
            )

            if not existing_log:
                # Log to DB only if not a duplicate
                log_entry = models.PredictionLog(
                    symbol=symbol,
                    current_price=result['current_price'],
                    predicted_direction=result['prediction'],
                    confidence_score=result['confidence'],
                    suggested_strategy=result['strategy'],
                    user_id=str(current_user.id)
                )
                await log_entry.insert()
            else:
                logger.info(f"Skipping DB log for {symbol} - duplicate within {config.DEDUPLICATION_WINDOW_MINS}m")
            # ---------------------------

            # Add Payoff Graph Data if strategy is clear
            payoff_data = []
            if "CE" in result['strategy']:
                strike = round(result['current_price'] / 50) * 50
                payoff_data = analyzer.generate_payoff_graph("CE", strike)
                result['strike'] = strike
                result['option_type'] = "CE"
            elif "PE" in result['strategy']:
                strike = round(result['current_price'] / 50) * 50
                payoff_data = analyzer.generate_payoff_graph("PE", strike)
                result['strike'] = strike
                result['option_type'] = "PE"
                
            result['payoff_graph'] = payoff_data
            
            # --- HFT Algo 5.1/5.2: Risk Management Integration ---
            from constants import OrderSide
            risk_engine = RiskEngine(account_balance=config.INITIAL_BALANCE)
            atr = analyzer.data['ATR'].iloc[-1]
            
            side = OrderSide.BUY if result['prediction'] == "BULLISH" else OrderSide.SELL
            risk_details = risk_engine.get_position_details(
                entry_price=result['current_price'],
                atr=atr,
                confidence=result['confidence'],
                side=side
            )
            
            result['hft_risk'] = risk_details
            
            # --- Automated Trade Execution (Simulation) ---
            if result['confidence'] >= 0.7:
                await trading_mgr.open_position(
                    user_id=str(current_user.id),
                    symbol=symbol,
                    side=side,
                    price=result['current_price'],
                    quantity=risk_details['quantity'],
                    strategy=result['strategy']
                )
            # -----------------------------------------------
            
            return result
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Prediction error for {symbol}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Prediction failed. Please try again later.")
        finally:
            # Optional: Cleanup lock if no one else is waiting
            # For simplicity in this demo, we keep them, but in production, 
            # we'd use a TTL cache for locks.
            pass

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
