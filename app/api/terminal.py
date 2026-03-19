from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.websocket_manager import ws_manager
from app.core import auth
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["Terminal WS"])

@router.websocket("/terminal/{client_id}")
async def websocket_terminal_endpoint(
    websocket: WebSocket, 
    client_id: str,
    token: str = Query(None)
):
    # Enforce authentication on handshake
    try:
        if not token:
            await websocket.accept()
            await websocket.close(code=4003, reason="Token missing")
            return
            
        # Verify token
        user = await auth.get_current_user(token)
        if not user or not user.is_approved:
            await websocket.accept()
            await websocket.close(code=4403, reason="Unauthorized or Pending Approval")
            return
            
        await ws_manager.connect_client(websocket)
    except Exception as e:
        logger.error(f"WS Auth Error for {client_id}: {e}")
        await websocket.close(code=4000)
        return

    try:
        while True:
            # We mostly broadcast, but we can handle inbound commands here
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle inbound terminal commands (e.g. subscribe to a new symbol)
            if message.get("type") == "SUBSCRIBE":
                symbol = message.get("symbol")
                # Handle subscription logic here if needed
                logger.info(f"Client {client_id} requested subscription to {symbol}")
            
    except WebSocketDisconnect:
        ws_manager.disconnect_client(websocket)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        ws_manager.disconnect_client(websocket)
