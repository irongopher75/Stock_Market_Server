from pydantic import BaseModel, EmailStr, BeforeValidator
from typing import Optional, List, Annotated
from datetime import datetime

# Helper to convert ObjectId to str
StrId = Annotated[str, BeforeValidator(str)]

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: Optional[StrId] = None
    is_active: bool
    is_superuser: bool
    is_approved: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class PredictionResult(BaseModel):
    prediction: str
    confidence: float
    rsi: float
    macd: float
    sma_20: float
    sma_50: float
    sma_200: float
    bb_upper: float
    bb_lower: float
    current_price: float
    strategy: str
    reasoning: str
    poc: Optional[float] = None
    vol_ratio: float
    strike: Optional[float] = None
    option_type: Optional[str] = None
    payoff_graph: List[dict]

class ManualTradeRequest(BaseModel):
    symbol: str
    side: str # BUY/SELL
    quantity: float
    price: float
