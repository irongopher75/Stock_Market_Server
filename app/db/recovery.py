from beanie import Document
from datetime import datetime, timezone
from typing import Optional, Dict, Any

class SystemState(Document):
    user_id: str
    last_known_balance: float
    active_positions: Dict[str, Any] = {} # {symbol: {quantity, entry_price, side}}
    last_updated: datetime = datetime.now(timezone.utc)
    is_emergency_halted: bool = False

    class Settings:
        name = "system_state"

async def save_state(user_id: str, balance: float, positions: Dict[str, Any]):
    """Persists current trading state to MongoDB."""
    state = await SystemState.find_one(SystemState.user_id == user_id)
    if not state:
        state = SystemState(user_id=user_id, last_known_balance=balance, active_positions=positions)
    else:
        state.last_known_balance = balance
        state.active_positions = positions
        state.last_updated = datetime.now(timezone.utc)
    await state.save()

async def get_state(user_id: str) -> Optional[SystemState]:
    """Retrieves the last persistent state for recovery."""
    return await SystemState.find_one(SystemState.user_id == user_id)

async def trigger_emergency_halt(user_id: str):
    """Flags the system as halted in case of catastrophic failure."""
    state = await SystemState.find_one(SystemState.user_id == user_id)
    if state:
        state.is_emergency_halted = True
        state.last_updated = datetime.now(timezone.utc)
        await state.save()
