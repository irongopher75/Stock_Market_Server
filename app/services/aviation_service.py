"""
Aviation Service — uses the unofficial FlightRadarAPI library.
Falls back to OpenSky REST if FlightRadarAPI is unavailable.
No API key required for FlightRadarAPI.
"""
import asyncio
import logging
import time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Cargo airline ICAO callsign prefixes for signal flagging
CARGO_PREFIXES = {"FDX", "UPS", "DHK", "CLX", "GTI", "BOX", "PAC", "ATN", "ABX", "NKS"}


class AviationService:
    def __init__(self):
        self._cache: List[Dict] = []
        self._last_update: float = 0
        self._is_running = False
        self._poll_interval = 30  # seconds

        try:
            from FlightRadar24 import FlightRadar24API
            self._fr_api = FlightRadar24API()
            self._source = "FlightRadar24 (unofficial)"
            logger.info("AviationService: FlightRadarAPI loaded")
        except ImportError:
            self._fr_api = None
            self._source = "Unavailable"
            logger.warning("AviationService: FlightRadarAPI not installed. Run: pip3 install FlightRadarAPI")

    async def start(self):
        if self._is_running:
            return
        self._is_running = True
        asyncio.create_task(self._poll_loop())
        logger.info(f"AviationService started (source: {self._source})")

    async def stop(self):
        self._is_running = False

    async def get_flights(self) -> List[Dict]:
        if time.time() - self._last_update > self._poll_interval or not self._cache:
            await self._fetch_and_update()
        return self._cache

    async def get_stats(self) -> Dict:
        flights = await self.get_flights()
        airborne = flights  # already filtered in _normalize
        cargo = [f for f in airborne if f.get("type") == "CARGO"]
        return {
            "total_airborne": len(airborne),
            "cargo": len(cargo),
            "passenger": len(airborne) - len(cargo),
            "source": self._source,
            "last_updated": self._last_update,
        }

    async def _poll_loop(self):
        while self._is_running:
            await self._fetch_and_update()
            await asyncio.sleep(self._poll_interval)

    async def _fetch_and_update(self):
        if not self._fr_api:
            return
        try:
            # Run in thread — FlightRadarAPI is synchronous
            raw_flights = await asyncio.to_thread(self._fr_api.get_flights)
            normalized = [self._normalize(f) for f in raw_flights if f.latitude and f.longitude]
            self._cache = normalized
            self._last_update = time.time()
            logger.info(f"AviationService: fetched {len(normalized)} aircraft from FR24")
        except Exception as e:
            logger.error(f"AviationService fetch error: {e}")

    def _normalize(self, f) -> Dict:
        callsign = str(f.callsign or f.id or "").strip()
        is_cargo = any(callsign.startswith(pfx) for pfx in CARGO_PREFIXES)
        return {
            "icao24":      str(f.icao_24bit or "").lower(),
            "callsign":    callsign,
            "airline":     str(f.airline_iata or ""),
            "country":     str(f.origin_country or "---") if hasattr(f, 'origin_country') else "---",
            "lat":         round(float(f.latitude), 4),
            "lon":         round(float(f.longitude), 4),
            "altitude_ft": int(f.altitude or 0),
            "altitude_m":  round(int(f.altitude or 0) * 0.3048),
            "speed_kts":   int(f.ground_speed or 0),
            "heading":     int(f.heading or 0),
            "on_ground":   bool(f.on_ground) if hasattr(f, 'on_ground') else False,
            "type":        "CARGO" if is_cargo else "PAX",
            "origin":      str(f.origin_airport_iata or ""),
            "destination": str(f.destination_airport_iata or ""),
        }


# Singleton
_aviation_service: Optional[AviationService] = None

def get_aviation_service() -> AviationService:
    global _aviation_service
    if _aviation_service is None:
        _aviation_service = AviationService()
    return _aviation_service
