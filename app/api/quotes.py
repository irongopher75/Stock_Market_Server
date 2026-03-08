from fastapi import APIRouter
import yfinance as yf
import logging
from typing import List

router = APIRouter(prefix="/api/v1/quotes", tags=["quotes"])
logger = logging.getLogger(__name__)

# Canonical symbol → yfinance ticker mapping
AXIOM_WATCHLIST = {
    "AAPL": "AAPL",
    "AMZN": "AMZN",
    "BABA": "BABA",
    "BTC/USD": "BTC-USD",
    "COST": "COST",
    "ETH/USD": "ETH-USD",
    "GOOGL": "GOOG",
    "HDFC": "HDFCBANK.NS",
    "INFY": "INFY.NS",
    "META": "META",
    "MSFT": "MSFT",
    "NFLX": "NFLX",
    "NVDA": "NVDA",
    "ONGC": "ONGC.NS",
    "QCOM": "QCOM",
    "RELIANCE": "RELIANCE.NS",
    "SBUX": "SBUX",
    "SOL/USD": "SOL-USD",
    "TCS": "TCS.NS",
    "TSLA": "TSLA",
    "UBER": "UBER",
    "WIPRO": "WIPRO.NS",
}

@router.get("/batch")
async def get_batch_quotes():
    """
    Returns last-traded prices for all AXIOM watchlist symbols via yfinance.
    No auth required — used to seed the terminal on startup with real data.
    """
    results = {}
    tickers = list(AXIOM_WATCHLIST.values())

    try:
        data = yf.download(
            tickers,
            period="2d",
            interval="1d",
            progress=False,
            threads=True,
            auto_adjust=True
        )["Close"]

        for display_name, yf_ticker in AXIOM_WATCHLIST.items():
            try:
                col = yf_ticker
                if col in data.columns:
                    series = data[col].dropna()
                    if not series.empty:
                        price = float(series.iloc[-1])
                        prev  = float(series.iloc[-2]) if len(series) > 1 else price
                        results[display_name] = {
                            "price": round(price, 2),
                            "prev_close": round(prev, 2),
                            "change_pct": round(((price - prev) / prev) * 100, 2) if prev else 0.0,
                            "up": price >= prev,
                            "stale": True,   # flag: last-close, not live tick
                        }
            except Exception as e:
                logger.warning(f"Failed to parse {display_name}: {e}")

    except Exception as e:
        logger.error(f"Batch quote fetch failed: {e}")

    return results
