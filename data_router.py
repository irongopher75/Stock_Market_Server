import os
import json
import logging
import asyncio
import pandas as pd
from typing import Dict, Any, Optional
import yfinance as yf
from utils.finnhub_client import FinnhubClient
from utils.breeze_client import BreezeClient
import config

logger = logging.getLogger(__name__)

# Redis could be used here, but we'll implement a fallback local cache for resilience
class LocalCache:
    def __init__(self):
        self.data = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str):
        async with self._lock:
            entry = self.data.get(key)
            if entry:
                if entry['expiry'] > asyncio.get_event_loop().time():
                    return entry['value']
                else:
                    del self.data[key]
            return None

    async def set(self, key: str, value: Any, ttl: int):
        async with self._lock:
            self.data[key] = {
                'value': value,
                'expiry': asyncio.get_event_loop().time() + ttl
            }

class DataRouter:
    """
    Orchestrates data fetching across providers with caching logic.
    Decouples providers from the ML Engine.
    """
    def __init__(self):
        self.finnhub = FinnhubClient()
        self.breeze = BreezeClient()
        self.cache = LocalCache()

    def _is_indian_market(self, symbol: str) -> bool:
        """Determines if the symbol belongs to NSE/BSE."""
        symbol = symbol.upper()
        # Basic heuristic: .NS, .BO or typical Indian symbols if mapping exists
        if any(suffix in symbol for suffix in [".NS", ".BO"]):
            return True
        # Check against ticker map or other heuristics if needed
        return False

    async def get_price_data(self, symbol: str, interval: str = "1h", period: str = "1mo") -> pd.DataFrame:
        """
        Routes the request to the appropriate data provider.
        Checks cache first.
        """
        cache_key = f"prices:{symbol}:{interval}:{period}"
        cached_df_json = await self.cache.get(cache_key)
        
        if cached_df_json:
            logger.info(f"Cache hit for {symbol}")
            return pd.read_json(cached_df_json)

        logger.info(f"Cache miss for {symbol}, routing to provider...")
        
        # 1. Indian Markets -> Breeze (Fallback to yfinance for now)
        if self._is_indian_market(symbol):
            # Currently Breeze is a placeholder, so we use yfinance as fallback
            df = await self._fetch_from_yfinance(symbol, interval, period)
        else:
            # 2. US/Global Markets -> Finnhub for real-time, yfinance for history
            # For 1mo data, yfinance is often more robust on free tiers
            df = await self._fetch_from_yfinance(symbol, interval, period)
            
            # Enrich with real-time quote from Finnhub if requested interval is small
            if interval in ["1m", "5m", "15m", "1h"]:
                quote = await self.finnhub.get_quote(symbol)
                if quote and 'c' in quote:
                    # Append or update the last price with Finnhub's real-time data
                    new_row = pd.DataFrame([{
                        "Open": quote['o'],
                        "High": quote['h'],
                        "Low": quote['l'],
                        "Close": quote['c'],
                        "Volume": quote['v'],
                        "Datetime": pd.to_datetime('now', utc=True)
                    }]).set_index("Datetime")
                    # Merge logic here (simple version: concat if time is newer)
                    df = pd.concat([df, new_row])
                    df = df[~df.index.duplicated(keep='last')]

        # Cache the result
        if not df.empty:
            await self.cache.set(cache_key, df.to_json(), config.CACHE_TTL_PRICE)
            
        return df

    async def _fetch_from_yfinance(self, symbol: str, interval: str, period: str) -> pd.DataFrame:
        """Helper to fetch bulk data from yfinance asynchronously."""
        ticker = yf.Ticker(symbol)
        data = await asyncio.to_thread(ticker.history, period=period, interval=interval)
        return data

    async def get_features(self, symbol: str, feature_key: str) -> Any:
        """Retrieve pre-computed features from cache."""
        return await self.cache.get(f"features:{symbol}:{feature_key}")

    async def set_features(self, symbol: str, feature_key: str, value: Any):
        """Cache computed features."""
        await self.cache.set(f"features:{symbol}:{feature_key}", value, config.CACHE_TTL_FEATURES)
