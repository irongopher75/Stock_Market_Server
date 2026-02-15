from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: Optional[str] = None
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
    current_price: float
    strategy: str
    strike: Optional[float] = None
    option_type: Optional[str] = None
    payoff_graph: List[dict]
