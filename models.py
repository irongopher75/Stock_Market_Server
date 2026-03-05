from beanie import Document
from datetime import datetime, timezone
from typing import Optional
from pydantic import Field

class User(Document):
    email: str
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    is_approved: bool = False

    class Settings:
        name = "users"

class PredictionLog(Document):
    symbol: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_price: float
    predicted_direction: str
    confidence_score: float
    suggested_strategy: str
    user_id: str # Reference to User ID

    class Settings:
        name = "prediction_logs"

class Trade(Document):
    symbol: str
    user_id: str
    side: str  # BUY/SELL (from OrderSide constant)
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    status: str = "OPEN"  # OPEN/CLOSED (from OrderStatus constant)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    exit_timestamp: Optional[datetime] = None
    pnl: float = 0.0
    strategy: Optional[str] = "MANUAL"
    current_price: Optional[float] = None

    class Settings:
        name = "trades"
