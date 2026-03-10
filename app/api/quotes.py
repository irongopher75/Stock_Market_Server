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
    "BTCUSDT": "BTC-USD",
    "COST": "COST",
    "ETHUSDT": "ETH-USD",
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
    "SOLUSDT": "SOL-USD",
    "TCS": "TCS.NS",
    "TSLA": "TSLA",
    "UBER": "UBER",
    "WIPRO": "WIPRO.NS",
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "DOW JONES": "^DJI",
    "S&P 500": "^GSPC",
}

@router.get("/batch")
async def get_batch_quotes(symbols: str = ""):
    """
    Returns last-traded prices for requested symbols (or AXIOM_WATCHLIST defaults).
    Used to seed the terminal with real-world data for any asset.
    """
    requested_symbols = symbols.split(",") if symbols else list(AXIOM_WATCHLIST.keys())
    results = {}
    
    # Map display names to yfinance tickers
    ticker_map = {}
    for sym in requested_symbols:
        ticker = AXIOM_WATCHLIST.get(sym, sym) # Fallback to literal if not in map
        ticker_map[ticker] = sym
        
    tickers = list(ticker_map.keys())

    try:
        # Fetch data via yfinance
        data = yf.download(
            tickers,
            period="2d",
            interval="1d",
            progress=False,
            threads=True,
            auto_adjust=True
        )
        
        close_data = data["Close"]
        
        for ticker, display_name in ticker_map.items():
            try:
                # Handle both single and multi-ticker returns from yfinance
                series = close_data[ticker] if len(tickers) > 1 else close_data
                series = series.dropna()
                
                if not series.empty:
                    price = float(series.iloc[-1])
                    prev  = float(series.iloc[-2]) if len(series) > 1 else price
                    
                    # Basic currency detection based on exchange suffix
                    currency = "INR" if ticker.endswith(".NS") or ticker.endswith(".BO") or ticker == "^NSEI" or ticker == "^BSESN" else "USD"
                    if "USDT" in display_name or "-" in ticker: # Crypto
                        currency = "USDT"

                    results[display_name] = {
                        "price": round(price, 2),
                        "prev_close": round(prev, 2),
                        "change_pct": round(((price - prev) / prev) * 100, 2) if prev else 0.0,
                        "up": price >= prev,
                        "currency": currency,
                        "stale": True, 
                    }
            except Exception as e:
                logger.warning(f"Failed to parse {display_name} ({ticker}): {e}")

    except Exception as e:
        logger.error(f"Batch quote fetch failed: {e}")

    return results
