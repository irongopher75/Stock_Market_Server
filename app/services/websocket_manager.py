import asyncio
import json
import logging
import websockets
import os
import ssl
from typing import Dict, Set, Any
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect

load_dotenv()

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Central Hub (Hub-and-Spoke)
    Normalizes feeds from Finnhub (Equities), AISStream (Vessels), and OpenSky (Aircraft).
    Exposes a single internal WebSocket for the AXIOM React frontend.
    """
    def __init__(self):
        self.finnhub_key = os.getenv("FINNHUB_API_KEY")
        self.active_clients: Set[WebSocket] = set()
        self.connections: Dict[str, Any] = {}
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._is_running = False
        
        # Lazy import to avoid circular dependency
        self.ais_service = None
        self.opensky_service = None
        
        # v3.0 Diff States
        self.last_vessel_state: Dict[str, Dict] = {} # mmsi -> data
        self.last_aircraft_state: Dict[str, Dict] = {} # callsign -> data

    async def start(self):
        if self._is_running:
            return
        self._is_running = True
        
        # Start Upstream Fetchers
        asyncio.create_task(self._finnhub_loop())
        
        from app.services.ais_service import AISService
        from app.services.opensky_service import OpenSkyService
        
        self.ais_service = AISService(self)
        self.opensky_service = OpenSkyService(self)
        
        await self.ais_service.start()
        await self.opensky_service.start()
        
        logger.info("Axiom WebSocket Hub started.")

    async def stop(self):
        self._is_running = False
        if self.ais_service: await self.ais_service.stop()
        if self.opensky_service: await self.opensky_service.stop()
        for ws in self.connections.values():
            if ws and hasattr(ws, 'close'): await ws.close()
        logger.info("Axiom WebSocket Hub stopped.")

    # --- Client Management ---
    async def connect_client(self, websocket: WebSocket):
        await websocket.accept()
        self.active_clients.add(websocket)
        logger.info(f"Client connected. Active: {len(self.active_clients)}")

    def disconnect_client(self, websocket: WebSocket):
        self.active_clients.remove(websocket)
        logger.info(f"Client disconnected. Active: {len(self.active_clients)}")

    async def broadcast_to_clients(self, message: dict):
        """Unified broadcast to all connected AXIOM terminals."""
        if not self.active_clients:
            return
        
        # Normalize and serialize
        payload = json.dumps(message)
        disconnected = set()
        
        for client in self.active_clients:
            try:
                await client.send_text(payload)
            except Exception:
                disconnected.add(client)
        
        for client in disconnected:
            self.disconnect_client(client)

    # --- Upstream Normalization & Broadcasting ---
    

    async def broadcast_vessel_data(self, current: list):
        """Broadcasts only the changed/new vessels (diff) to save bandwidth."""
        current_map = {v['mmsi']: v for v in current}
        
        updated = [
            v for mmsi, v in current_map.items()
            if mmsi not in self.last_vessel_state or 
            self.last_vessel_state[mmsi].get('lat') != v.get('lat') or
            self.last_vessel_state[mmsi].get('lon') != v.get('lon')
        ]
        
        removed = [
            mmsi for mmsi in self.last_vessel_state
            if mmsi not in current_map
        ]
        
        if updated or removed:
            message = {
                "type": "VESSEL_DIFF",
                "payload": {
                    "updated": updated,
                    "removed": removed
                },
                "timestamp": asyncio.get_event_loop().time()
            }
            await self.broadcast_to_clients(message)
            self.last_vessel_state = current_map

    async def broadcast_aircraft_data(self, current: list):
        """Broadcasts only the changed/new aircraft (diff)."""
        # Assuming aircraft have a unique 'callsign' or 'icao24'
        current_map = {a['callsign']: a for a in current}
        
        updated = [
            a for callsign, a in current_map.items()
            if callsign not in self.last_aircraft_state or 
            self.last_aircraft_state[callsign].get('lat') != a.get('lat') or
            self.last_aircraft_state[callsign].get('lon') != a.get('lon')
        ]
        
        removed = [
            callsign for callsign in self.last_aircraft_state
            if callsign not in current_map
        ]
        
        if updated or removed:
            message = {
                "type": "AIRCRAFT_DIFF",
                "payload": {
                    "updated": updated,
                    "removed": removed
                },
                "timestamp": asyncio.get_event_loop().time()
            }
            await self.broadcast_to_clients(message)
            self.last_aircraft_state = current_map

    async def _broadcast_trade(self, trades: list):
        """Normalize and broadcast Finnhub trade data."""
        for trade in trades:
            message = {
                "type": "EQUITY",
                "symbol": trade["s"],
                "price": trade["p"],
                "volume": trade["v"],
                "timestamp": trade["t"]
            }
            await self.broadcast_to_clients(message)

    # --- Finnhub Internal Logic ---
    async def _finnhub_loop(self):
        uri = f"wss://ws.finnhub.io?token={self.finnhub_key}"
        while self._is_running:
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                async with websockets.connect(uri, ssl=ssl_context) as websocket:
                    self.connections["finnhub"] = websocket
                    # Auto-subscribe to a default set for testing
                    stocks = ["AAPL", "NVDA", "TSLA", "BINANCE:BTCUSDT"]
                    for s in stocks:
                        await websocket.send(json.dumps({"type": "subscribe", "symbol": s}))

                    async for message in websocket:
                        if not self._is_running: break
                        data = json.loads(message)
                        if data.get("type") == "trade":
                            await self._broadcast_trade(data["data"])
            except Exception as e:
                logger.error(f"Finnhub error: {e}. Reconnecting...")
                await asyncio.sleep(5)

# Global instance
ws_manager = WebSocketManager()
