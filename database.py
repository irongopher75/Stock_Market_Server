import motor.motor_asyncio
from beanie import init_beanie
import os
import models

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/stock_market_db")

import certifi

async def init_db():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017/stock_market_db")
    client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url, tlsCAFile=certifi.where())
    await init_beanie(
        database=client.get_default_database(),
        document_models=[
            models.User,
            models.PredictionLog
        ]
    )
