import os
import time
import requests
import asyncio
import aiohttp
import logging
from typing import Dict, Optional, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class FinnhubClient:
    """
    Finnhub API Client with built-in rate limiting (60 RPM).
    Uses a simple timestamp-based gate for the free tier.
    """
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY")
        self.last_request_time = 0
        self.request_interval = 1.01  # Slightly more than 1 second to stay under 60 RPM
        self._lock = asyncio.Lock()

    async def _throttle(self):
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.request_interval:
                await asyncio.sleep(self.request_interval - elapsed)
            self.last_request_time = time.time()

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch real-time quote for a symbol."""
        await self._throttle()
        url = f"{self.BASE_URL}/quote"
        params = {"symbol": symbol, "token": self.api_key}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        logger.warning("Finnhub Rate Limit Hit (429). Retrying after delay...")
                        await asyncio.sleep(5)
                        return await self.get_quote(symbol)
                    else:
                        error_text = await response.text()
                        logger.error(f"Finnhub API error: {response.status} - {error_text}")
                        return {}
            except Exception as e:
                logger.error(f"Finnhub connection error: {str(e)}")
                return {}

    async def get_basic_financials(self, symbol: str) -> Dict[str, Any]:
        """Fetch basic financial data."""
        await self._throttle()
        url = f"{self.BASE_URL}/stock/metric"
        params = {"symbol": symbol, "metric": "all", "token": self.api_key}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                return {}

    async def get_technical_indicators(self, symbol: str, resolution: str = "D") -> Dict[str, Any]:
        """Fetch technical indicators (if available in tier)."""
        # Note: Some technical indicators are paid in Finnhub
        await self._throttle()
        url = f"{self.BASE_URL}/indicator"
        # Example for RSI
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "indicator": "rsi",
            "timeperiod": 14,
            "token": self.api_key
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                return {}
