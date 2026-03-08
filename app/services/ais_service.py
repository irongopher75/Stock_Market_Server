import asyncio
import json
import logging
import websockets
import os
import ssl
import time
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AISService:
    def __init__(self, websocket_manager):
        self.api_key = os.getenv("AISSTREAM_API_KEY")
        self.ws_manager = websocket_manager
        self.uri = "wss://stream.aisstream.io/v0/stream"
        self._is_running = False
        self._cache: Dict[str, Dict] = {} # mmsi -> normalized_data
        self._last_update = 0

    async def start(self):
        if self._is_running:
            return
        self._is_running = True
        asyncio.create_task(self._stream_loop())
        logger.info("AIS Service started.")

    async def stop(self):
        self._is_running = False
        logger.info("AIS Service stopped.")

    async def get_vessels(self) -> List[Dict]:
        # Return flattened cache
        return list(self._cache.values())

    def _normalize(self, data: dict) -> Dict:
        """Flattens the deeply nested AISStream JSON into a clean terminal-ready format."""
        msg_type = data.get("MessageType")
        meta = data.get("MetaData", {})
        mmsi = str(meta.get("MMSI", ""))
        
        # We only care about PositionReport and ShipStaticData
        # AISStream sends them separately. We merge them in our cache if they share MMSI.
        existing = self._cache.get(mmsi, {
            "mmsi": mmsi,
            "name": meta.get("ShipName", "UNKNOWN vessel").strip(),
            "lat": meta.get("latitude"),
            "lon": meta.get("longitude"),
            "type": "General Cargo",
            "destination": "---",
            "speed": 0,
            "heading": 0,
            "flag": "---"
        })

        if msg_type == "PositionReport":
            pos = data.get("Message", {}).get("PositionReport", {})
            existing["lat"] = pos.get("Latitude")
            existing["lon"] = pos.get("Longitude")
            existing["speed"] = pos.get("Sog", 0)
            existing["heading"] = pos.get("TrueHeading", 0)
        
        elif msg_type == "ShipStaticData":
            static = data.get("Message", {}).get("ShipStaticData", {})
            existing["name"] = static.get("Name", existing["name"]).strip()
            existing["type"] = static.get("ShipType", existing["type"])
            existing["destination"] = static.get("Destination", existing["destination"]).strip()
            # simple flag mapping placeholder or extracted from metadata if possible
            
        return existing

    async def _stream_loop(self):
        while self._is_running:
            try:
                if not self.api_key:
                    logger.warning("AISSTREAM_API_KEY missing. AIS service suspended.")
                    return

                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                async with websockets.connect(self.uri, ssl=ssl_context, open_timeout=30) as ws:
                    subscribe_msg = {
                        "APIKey": self.api_key,
                        "BoundingBoxes": [[[-90, -180], [90, 180]]],
                        "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    
                    async for msg in ws:
                        if not self._is_running:
                            break
                        raw_data = json.loads(msg)
                        normalized = self._normalize(raw_data)
                        
                        # Only cache if we have coordinates
                        if normalized["lat"] and normalized["lon"]:
                            self._cache[normalized["mmsi"]] = normalized
                        
                        # Throttle broadcasts to once every 2 seconds to avoid flooding frontend
                        if now - self._last_update > 2:
                            # Send the whole visible fleet to all terminals (WS Manager now handles the diff)
                            await self.ws_manager.broadcast_vessel_data(list(self._cache.values())[:300]) 
                            self._last_update = now

            except Exception as e:
                logger.error(f"AIS Stream error: {e}. Reconnecting in 10s...")
                await asyncio.sleep(10)
