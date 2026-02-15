from beanie import Document
from datetime import datetime
from typing import Optional

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
    timestamp: datetime = datetime.utcnow()
    current_price: float
    predicted_direction: str
    confidence_score: float
    suggested_strategy: str
    user_id: str # Reference to User ID

    class Settings:
        name = "prediction_logs"
