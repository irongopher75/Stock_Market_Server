from fastapi import APIRouter, Depends, HTTPException
import models, auth
from backtester import VectorizedBacktester
from typing import List
import os
import config
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])

@router.post("/run")
async def run_backtest(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
    initial_capital: float = 100000.0,
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Executes a vectorized backtest and stores results."""
    try:
        tester = VectorizedBacktester(symbol, initial_capital=initial_capital)
        results = await tester.run(period=period, interval=interval)
        
        # Persist to DB
        backtest_run = models.BacktestRun(
            symbol=symbol,
            user_id=str(current_user.id),
            period=period,
            interval=interval,
            metrics=results,
            equity_curve=results["equity_curve"],
            config={
                "initial_capital": initial_capital,
                "strategy": "Regime-Aware Ensemble"
            }
        )
        await backtest_run.insert()
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

@router.get("/history", response_model=List[models.BacktestRun])
async def get_backtest_history(
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Retrieves previous backtest runs for the current user."""
    return await models.BacktestRun.find(models.BacktestRun.user_id == str(current_user.id)).sort("-timestamp").to_list()

@router.get("/{run_id}", response_model=models.BacktestRun)
async def get_backtest_result(
    run_id: str,
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Retrieves a specific backtest run result."""
    run = await models.BacktestRun.get(run_id)
    if not run or run.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return run
