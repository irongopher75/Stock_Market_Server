"""
OpenSky Network Service — Authenticated polling with Basic Auth.
Fetches live aircraft states, normalizes them, caches results.
"""
import httpx
import asyncio
import logging
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

OPENSKY_USER = os.getenv("OPENSKY_USERNAME", "")
OPENSKY_PASS = os.getenv("OPENSKY_PASSWORD", "")
BASE_URL     = "https://opensky-network.org/api"

# Authenticated users get 4,000 API credits/day (each /states/all call costs 1 credit per 10 seconds)
# We poll every 30s to stay well within limits
POLL_INTERVAL = 30  # seconds

# Bounding boxes to query (lat_min, lon_min, lat_max, lon_max)
# Focus on high-interest aviation regions
REGIONS = {
    "GLOBAL": None,   # None = no bbox filter (all states, throttled)
}

# Column order from OpenSky REST API
STATE_COLS = [
    "icao24", "callsign", "origin_country", "time_position",
    "last_contact", "longitude", "latitude", "baro_altitude",
    "on_ground", "velocity", "true_track", "vertical_rate",
    "sensors", "geo_altitude", "squawk", "spi", "position_source"
]

# ICAO prefix → country
ICAO_COUNTRY = {
    "a": "USA", "4b": "India", "4c": "India", "4d": "India",
    "3c": "Germany", "4ca": "Ireland", "76": "Mexico",
    "e4": "Brazil", "71": "UK", "7c": "Australia",
    "b8": "China", "86": "Japan"
}

# Well-known cargo airline ICAO callsign prefixes
CARGO_CALLSIGNS = {"FDX", "UPS", "DHK", "CLX", "GTI", "BOX", "PAC", "ATN", "ABX"}


class OpenSkyService:
    def __init__(self, websocket_manager=None):
        self.ws_manager   = websocket_manager
        self._is_running  = False
        self._cache: List[Dict] = []
        self._last_update: float = 0
        self.daily_calls = 0  # Tracking for adaptive budget
        self.current_interval = POLL_INTERVAL

        if OPENSKY_USER and OPENSKY_PASS:
            self._auth = httpx.BasicAuth(OPENSKY_USER, OPENSKY_PASS)
            logger.info(f"OpenSky: authenticated as {OPENSKY_USER}")
        else:
            self._auth = None
            logger.warning("OpenSky: running unauthenticated (100 credits/day limit)")

    async def start(self):
        if self._is_running:
            return
        self._is_running = True
        asyncio.create_task(self._poll_loop())
        logger.info("OpenSky Service started (Adaptive polling enabled)")

    async def stop(self):
        self._is_running = False

    async def get_flights(self) -> List[Dict]:
        """Returns cached flight list for REST endpoints. Refreshes if stale."""
        import time
        if time.time() - self._last_update > self.current_interval or not self._cache:
            await self._fetch_and_update()
        return self._cache

    async def _poll_loop(self):
        while self._is_running:
            await self._fetch_and_update()
            
            # Broadcast incremental diffs via WS Manager
            if self.ws_manager and self._cache:
                await self.ws_manager.broadcast_aircraft_data(self._cache[:300])
            
            # Adaptive interval logic
            # Authenticated budget: 4000 calls/day. 
            # Utilization factor scales interval from 10s to 60s.
            limit = 4000 if self._auth else 100
            utilization = self.daily_calls / limit
            self.current_interval = 10 + (utilization * 50) 
            
            await asyncio.sleep(self.current_interval)

    async def _fetch_and_update(self):
        import time
        try:
            async with httpx.AsyncClient(timeout=15, auth=self._auth) as client:
                resp = await client.get(f"{BASE_URL}/states/all")
                self.daily_calls += 1
                
                if resp.status_code == 200:
                    data = resp.json()
                    states = data.get("states") or []
                    self._cache = [self._normalize(s) for s in states if s[5] and s[6]]  # must have lon/lat
                    self._last_update = time.time()
                    logger.info(f"OpenSky: fetched {len(self._cache)} aircraft (Daily calls: {self.daily_calls})")
                elif resp.status_code == 429:
                    logger.warning("OpenSky: rate limited (429) — cooling down")
                    self.current_interval = 300 # 5 min cooldown
                else:
                    logger.warning(f"OpenSky API error: {resp.status_code}")
        except Exception as e:
            logger.error(f"OpenSky fetch error: {e}")

    def _normalize(self, s: list) -> Dict:
        """Map raw state vector to a clean dict."""
        callsign = (s[1] or "").strip()
        icao = (s[0] or "").lower()
        is_cargo = any(callsign.startswith(pfx) for pfx in CARGO_CALLSIGNS)

        return {
            "icao24":     icao,
            "callsign":   callsign or icao.upper(),
            "country":    s[2] or "---",
            "lon":        round(s[5], 4) if s[5] else None,
            "lat":        round(s[6], 4) if s[6] else None,
            "altitude_m": round(s[7], 0) if s[7] else 0,
            "altitude_ft": round((s[7] or 0) * 3.281),
            "on_ground":  s[8] or False,
            "speed_ms":   s[9] or 0,
            "speed_kts":  round((s[9] or 0) * 1.944),
            "heading":    round(s[10] or 0),
            "type":       "CARGO" if is_cargo else "PAX",
            "squawk":     s[14] or "",
        }


# Singleton — instantiated by main.py / websocket_manager
opensky_service: Optional[OpenSkyService] = None

def get_opensky_service() -> OpenSkyService:
    global opensky_service
    if opensky_service is None:
        opensky_service = OpenSkyService()
    return opensky_service
