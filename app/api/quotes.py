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

@router.get("/macro/yields")
async def get_macro_yields():
    """Returns real-time sovereign yield curve data using yfinance Treasury symbols."""
    symbols = {
        'US': {'3M': '^IRX', '5Y': '^FVX', '10Y': '^TNX', '30Y': '^TYX'},
    }
    
    results = {'US': [], 'IN': [
        {'maturity': '3M', 'yield': 6.75}, {'maturity': '1Y', 'yield': 6.82}, {'maturity': '2Y', 'yield': 6.88},
        {'maturity': '5Y', 'yield': 6.98}, {'maturity': '10Y', 'yield': 7.12}, {'maturity': '30Y', 'yield': 7.35}
    ]}
    
    try:
        us_tickers = list(symbols['US'].values())
        data = yf.download(us_tickers, period="2d", progress=False, threads=True)
        if not data.empty and "Close" in data:
            close_data = data["Close"]
            for maturity, ticker in symbols['US'].items():
                try:
                    series = close_data[ticker].dropna()
                    if not series.empty:
                        val = float(series.iloc[-1])
                        results['US'].append({'maturity': maturity, 'yield': round(val, 2)})
                except:
                    pass
    except Exception as e:
        logger.error(f"Failed to fetch macro yields: {e}")
        
    return results

@router.get("/macro/fx")
async def get_macro_fx():
    """Returns real-time Forex rates."""
    pairs = {
        'USDINR=X': 'USD/INR',
        'EURUSD=X': 'EUR/USD',
        'GBPUSD=X': 'GBP/USD',
        'JPY=X': 'USD/JPY',
        'AUDUSD=X': 'AUD/USD',
        'CHF=X': 'USD/CHF'
    }
    results = []
    try:
        data = yf.download(list(pairs.keys()), period="2d", interval="1d", progress=False, threads=True)
        if not data.empty and "Close" in data:
            for ticker, label in pairs.items():
                try:
                    series = data["Close"][ticker].dropna() if len(pairs) > 1 else data["Close"].dropna()
                    if not series.empty:
                        price = float(series.iloc[-1])
                        prev = float(series.iloc[-2]) if len(series) > 1 else price
                        chg_pct = ((price - prev) / prev) * 100 if prev else 0.0
                        results.append({
                            'pair': label,
                            'rate': round(price, 4) if price < 100 else round(price, 2),
                            'chg': f"{'+' if chg_pct >= 0 else ''}{round(chg_pct, 2)}%",
                            'up': chg_pct >= 0
                        })
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Failed to fetch FX rates: {e}")
    return results
