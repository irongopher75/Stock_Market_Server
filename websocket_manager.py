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

    async def start(self):
        if self._is_running:
            return
        self._is_running = True
        
        # Start Upstream Fetchers
        asyncio.create_task(self._finnhub_loop())
        
        from services.ais_service import AISService
        from services.opensky_service import OpenSkyService
        
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
    
    async def broadcast_vessel_data(self, data: dict):
        """Normalize and broadcast AIS data."""
        message = {
            "type": "VESSEL",
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast_to_clients(message)

    async def broadcast_aircraft_data(self, data: dict):
        """Normalize and broadcast OpenSky data."""
        message = {
            "type": "AIRCRAFT",
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast_to_clients(message)

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
