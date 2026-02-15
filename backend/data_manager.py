import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def fetch_stock_history(symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetches historical data for a given symbol using yfinance.
    
    Args:
        symbol (str): The stock symbol (e.g., ^NSEI for NIFTY 50).
        period (str): The history period to fetch (default "2y").
        interval (str): The data interval (default "1d").
    
    Returns:
        pd.DataFrame: DataFrame containing the historical data.
    """
    # Append .NS for NSE stocks if not an index like ^NSEI or ^NSEBANK
    ticker_symbol = symbol
    if not symbol.startswith("^") and not symbol.endswith(".NS"):
        ticker_symbol = f"{symbol}.NS"
        
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period=period, interval=interval)
    
    if df.empty:
        raise ValueError(f"No data found for symbol {ticker_symbol}")
        
    return df

def get_current_price(symbol: str) -> float:
    """
    Fetches the latest execution price.
    """
    ticker_symbol = symbol
    if not symbol.startswith("^") and not symbol.endswith(".NS"):
        ticker_symbol = f"{symbol}.NS"
    
    ticker = yf.Ticker(ticker_symbol)
    # Fast fetch using 'fast_info' or 'history' last row
    try:
        price = ticker.fast_info['last_price']
        return price
    except:
        # Fallback to history
        df = ticker.history(period="1d")
        if not df.empty:
            return df["Close"].iloc[-1]
        return 0.0

# Future: Add Option Chain Scraping here using nsepython or simple requests
