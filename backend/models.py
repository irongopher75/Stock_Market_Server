from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False) # True for Admin
    is_approved = Column(Boolean, default=False) # Must be approved by Admin to login
    
    prediction_logs = relationship("PredictionLog", back_populates="owner")

class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True) # e.g. NIFTY, BANKNIFTY
    timestamp = Column(DateTime, default=datetime.utcnow)
    current_price = Column(Float)
    predicted_direction = Column(String) # "BULLISH", "BEARISH", "NEUTRAL"
    confidence_score = Column(Float)
    suggested_strategy = Column(String) # JSON string or text description of strategy
    
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="prediction_logs")
