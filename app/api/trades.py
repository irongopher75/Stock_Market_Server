from fastapi import APIRouter, Depends, HTTPException
from app.db import models, schemas
from app.core import auth
from typing import List

router = APIRouter(prefix="/trades", tags=["trades"])

@router.get("/active", response_model=List[models.Trade])
async def get_active_positions(
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Returns all open paper trades for the current user, appending current_price."""
    import yfinance as yf
    active_trades = await models.Trade.find(
        models.Trade.user_id == str(current_user.id),
        models.Trade.status == "OPEN"
    ).to_list()
    
    if active_trades:
        symbols = list(set([t.symbol for t in active_trades]))
        yf_symbols = []
        for s in symbols:
            if s == "NIFTY": yf_symbols.append("^NSEI")
            elif s == "BANKNIFTY": yf_symbols.append("^NSEBANK")
            elif "." not in s and not s.startswith("^"): yf_symbols.append(f"{s}.NS")
            else: yf_symbols.append(s)
            
        try:
            import asyncio
            data_df = await asyncio.to_thread(yf.download, yf_symbols, period="1d", interval="1m", progress=False)
            data = data_df['Close']
            for trade in active_trades:
                if trade.symbol == "NIFTY": price_col = "^NSEI"
                elif trade.symbol == "BANKNIFTY": price_col = "^NSEBANK"
                elif "." not in trade.symbol and not trade.symbol.startswith("^"): price_col = f"{trade.symbol}.NS"
                else: price_col = trade.symbol
                
                try:
                    current_price = data[price_col].iloc[-1] if len(yf_symbols) > 1 else data.iloc[-1]
                    trade.current_price = float(current_price)
                except:
                    pass
        except:
            pass
            
    return active_trades

@router.get("/history", response_model=List[models.Trade])
async def get_trade_history(
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Returns all closed paper trades for the current user."""
    return await models.Trade.find(
        models.Trade.user_id == str(current_user.id),
        models.Trade.status == "CLOSED"
    ).sort("-exit_timestamp").to_list()

@router.get("/performance")
async def get_performance_snapshot(
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Calculates realized/unrealized P&L, Total Equity, and Active Exposure."""
    from app.core import config
    import yfinance as yf
    
    # 1. Realized History
    history_trades = await models.Trade.find(
        models.Trade.user_id == str(current_user.id),
        models.Trade.status == "CLOSED"
    ).to_list()
    
    realized_pnl = sum(t.pnl for t in history_trades)
    wins = len([t for t in history_trades if t.pnl > 0])
    total_closed = len(history_trades)
    win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
    
    # Advanced Metrics
    gross_profit = sum(t.pnl for t in history_trades if t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in history_trades if t.pnl < 0))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (round(gross_profit, 2) if gross_profit > 0 else 0)
    
    strategy_breakdown = {}
    for t in history_trades:
        strat = t.strategy or "MANUAL"
        if strat.startswith("HFT"):
            if "Moderate Bullish" in strat: strat = "Moderate Bullish"
            elif "High Confidence Bullish" in strat: strat = "High Confidence Bullish"
            elif "Moderate Bearish" in strat: strat = "Moderate Bearish"
            elif "High Confidence Bearish" in strat: strat = "High Confidence Bearish"
        if strat not in strategy_breakdown:
            strategy_breakdown[strat] = {"count": 0, "pnl": 0}
        strategy_breakdown[strat]["count"] += 1
        strategy_breakdown[strat]["pnl"] += t.pnl
        
    formatted_strategies = [{"name": k, "value": v["count"], "pnl": v["pnl"]} for k, v in strategy_breakdown.items()]
    
    equity = config.INITIAL_BALANCE
    peak = equity
    max_dd = 0
    import numpy as np
    returns = []
    
    for t in sorted(history_trades, key=lambda x: x.exit_timestamp or x.timestamp):
        equity += t.pnl
        returns.append(t.pnl / config.INITIAL_BALANCE)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak
        if dd > max_dd:
            max_dd = dd
            
    max_drawdown_pct = round(max_dd * 100, 2)
    recovery_factor = round(realized_pnl / (peak * max_dd), 2) if max_dd > 0 else 0
    sharpe_ratio = round(np.mean(returns) / np.std(returns) * np.sqrt(252), 2) if len(returns) > 1 and np.std(returns) > 0 else 0
    
    # 2. Unrealized P&L & Exposure
    active_trades = await models.Trade.find(
        models.Trade.user_id == str(current_user.id),
        models.Trade.status == "OPEN"
    ).to_list()
    
    unrealized_pnl = 0.0
    total_exposure = 0.0
    
    # Optimization: Batch fetch prices if multiple trades exist
    if active_trades:
        symbols = list(set([t.symbol for t in active_trades]))
        # Map symbols for yf (NIFTY -> ^NSEI, etc.)
        yf_symbols = []
        for s in symbols:
            if s == "NIFTY": yf_symbols.append("^NSEI")
            elif s == "BANKNIFTY": yf_symbols.append("^NSEBANK")
            elif "." not in s and not s.startswith("^"): yf_symbols.append(f"{s}.NS")
            else: yf_symbols.append(s)
            
        import asyncio
        data_df = await asyncio.to_thread(yf.download, yf_symbols, period="1d", interval="1m", progress=False)
        data = data_df['Close']
        
        for trade in active_trades:
            # Handle both Series (1 symbol) and DataFrame (multiple)
            price_col = trade.symbol
            if trade.symbol == "NIFTY": price_col = "^NSEI"
            elif trade.symbol == "BANKNIFTY": price_col = "^NSEBANK"
            elif "." not in trade.symbol and not trade.symbol.startswith("^"): price_col = f"{trade.symbol}.NS"
            else: price_col = trade.symbol
            
            try:
                current_price = data[price_col].iloc[-1] if len(yf_symbols) > 1 else data.iloc[-1]
                if trade.side == "BUY":
                    unrealized_pnl += (current_price - trade.entry_price) * trade.quantity
                else:
                    unrealized_pnl += (trade.entry_price - current_price) * trade.quantity
                total_exposure += current_price * trade.quantity
            except:
                continue

    total_equity = config.INITIAL_BALANCE + realized_pnl + unrealized_pnl
    
    return {
        "initial_balance": config.INITIAL_BALANCE,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": realized_pnl + unrealized_pnl, # Net change
        "total_equity": total_equity,
        "active_exposure": total_exposure,
        "active_units": len(active_trades),
        "win_rate": f"{win_rate:.1f}%",
        "total_trades": total_closed,
        "currency": "₹",
        "server_time": datetime.now().strftime("%H:%M:%S"),
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_drawdown_pct,
        "sharpe_ratio": sharpe_ratio,
        "recovery_factor": recovery_factor,
        "strategy_breakdown": formatted_strategies
    }
    
@router.get("/config")
async def get_system_config():
    from app.core import config
    return {
        "initial_balance": config.INITIAL_BALANCE,
        "margin_multiplier": 0.2
    }

@router.get("/export")
async def export_trades_csv(
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Generates a CSV of all closed trades for the current user."""
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    trades = await models.Trade.find(
        models.Trade.user_id == str(current_user.id),
        models.Trade.status == "CLOSED"
    ).sort("-exit_timestamp").to_list()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["Timestamp", "Instrument", "Strategy", "Side", "Entry Price", "Exit Price", "Quantity", "PnL", "Status"])
    
    for t in trades:
        writer.writerow([
            t.exit_timestamp.strftime("%Y-%m-%d %H:%M:%S") if t.exit_timestamp else t.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            t.symbol,
            t.strategy,
            t.side,
            t.entry_price,
            t.exit_price or 0,
            t.quantity,
            t.pnl,
            t.status
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=trades_export_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

from app.services.trading_manager import TradingManager
trading_mgr = TradingManager()

@router.post("/execute", response_model=models.Trade)
async def execute_trade(
    request: schemas.ManualTradeRequest,
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Executes a manual paper trade."""
    trade = await trading_mgr.open_position(
        user_id=str(current_user.id),
        symbol=request.symbol,
        side=request.side,
        price=request.price,
        quantity=request.quantity
    )
    if not trade:
        raise HTTPException(status_code=400, detail="Trade execution failed.")
    return trade

@router.post("/close/{trade_id}", response_model=models.Trade)
async def close_trade(
    trade_id: str,
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Closes an active paper trade."""
    trade = await trading_mgr.close_position(
        user_id=str(current_user.id),
        trade_id=trade_id
    )
    if not trade:
        raise HTTPException(status_code=400, detail="Trade closure failed. Position might already be closed.")
    return trade
