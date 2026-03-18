from fastapi import APIRouter, Depends, HTTPException
from app.db import models, schemas
from app.core import auth
from typing import List

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/pending-users", response_model=List[schemas.User])
async def get_pending_users(current_user: models.User = Depends(auth.get_current_admin)):
    return await models.User.find(models.User.is_approved == False).to_list()

@router.get("/users-overview")
async def get_users_overview(current_user: models.User = Depends(auth.get_current_admin)):
    """Fetches all approved users and their active portfolio holdings with live pricing."""
    from app.core import config
    import yfinance as yf
    import asyncio
    
    # 1. Get all approved non-admin users
    users = await models.User.find(
        models.User.is_approved == True,
        models.User.is_superuser == False
    ).to_list()
    
    overview_data = []
    
    # Process each user
    for user in users:
        # Get active trades
        active_trades = await models.Trade.find(
            models.Trade.user_id == str(user.id),
            models.Trade.status == "OPEN"
        ).to_list()
        
        user_portfolio = {
            "id": str(user.id),
            "email": user.email,
            "status": "Active" if user.is_active else "Inactive",
            "initial_balance": config.INITIAL_BALANCE,
            "holdings": [],
            "total_exposure": 0.0,
            "unrealized_pnl": 0.0,
            "total_equity": config.INITIAL_BALANCE  # Will add realized PnL later
        }
        
        # Get realized PnL for accurate total equity
        closed_trades = await models.Trade.find(
            models.Trade.user_id == str(user.id),
            models.Trade.status == "CLOSED"
        ).to_list()
        realized_pnl = sum([t.pnl for t in closed_trades])
        user_portfolio["total_equity"] += realized_pnl
        
        if not active_trades:
            overview_data.append(user_portfolio)
            continue
            
        # Fetch live prices for active holdings
        symbols = list(set([t.symbol for t in active_trades]))
        yf_symbols = []
        for s in symbols:
            if s == "NIFTY": yf_symbols.append("^NSEI")
            elif s == "BANKNIFTY": yf_symbols.append("^NSEBANK")
            elif "." not in s and not s.startswith("^"): yf_symbols.append(f"{s}.NS")
            else: yf_symbols.append(s)
            
        try:
            data_df = await asyncio.to_thread(yf.download, yf_symbols, period="1d", interval="1m", progress=False)
            data = data_df['Close'] if 'Close' in data_df else data_df
            
            for trade in active_trades:
                price_col = trade.symbol
                if trade.symbol == "NIFTY": price_col = "^NSEI"
                elif trade.symbol == "BANKNIFTY": price_col = "^NSEBANK"
                elif "." not in trade.symbol and not trade.symbol.startswith("^"): price_col = f"{trade.symbol}.NS"
                
                try:
                    current_price = float(data[price_col].iloc[-1]) if len(yf_symbols) > 1 else float(data.iloc[-1])
                    
                    pnl = 0.0
                    if trade.side == "BUY":
                        pnl = (current_price - trade.entry_price) * trade.quantity
                    else:
                        pnl = (trade.entry_price - current_price) * trade.quantity
                        
                    exposure = current_price * trade.quantity
                    user_portfolio["total_exposure"] += exposure
                    user_portfolio["unrealized_pnl"] += pnl
                    
                    user_portfolio["holdings"].append({
                        "trade_id": str(trade.id),
                        "symbol": trade.symbol,
                        "side": trade.side,
                        "quantity": trade.quantity,
                        "entry_price": trade.entry_price,
                        "current_price": current_price,
                        "pnl": pnl,
                        "pnl_pct": (pnl / (trade.entry_price * trade.quantity)) * 100 if trade.entry_price > 0 else 0,
                        "timestamp": trade.timestamp
                    })
                except Exception as e:
                    pass
        except Exception as e:
            pass
            
        user_portfolio["total_equity"] += user_portfolio["unrealized_pnl"]
        overview_data.append(user_portfolio)
        
    return overview_data

@router.post("/approve/{user_id}")
async def approve_user(user_id: str, current_user: models.User = Depends(auth.get_current_admin)):
    user = await models.User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_approved = True
    await user.save()
    return {"message": f"User {user.email} approved"}
