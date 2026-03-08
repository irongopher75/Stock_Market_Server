import asyncio
import models
from trading_manager import TradingManager
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def test_trading():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URL'))
    await init_beanie(database=client.get_default_database(), document_models=[models.User, models.PredictionLog, models.Trade])
    
    user = await models.User.find_one()
    if not user:
        print("No user found")
        return
        
    mgr = TradingManager()
    
    # 1. Open a trade
    print("--- OPENING TRADE ---")
    trade = await mgr.open_position(
        user_id=str(user.id),
        symbol="RELIANCE",
        side="BUY",
        price=2500.0,
        quantity=10
    )
    print(f"Opened: {trade.id} for {trade.symbol}")
    
    # 2. Close it
    print("--- CLOSING TRADE ---")
    closed = await mgr.close_position(
        user_id=str(user.id),
        trade_id=str(trade.id),
        current_price=2600.0 # Force a profit of 1000
    )
    
    if closed:
        print(f"Closed: {closed.id} P&L: {closed.pnl}")
        assert closed.pnl == 1000.0
        print("SUCCESS: Trade closed and P&L verified.")
    else:
        print("FAILED: Trade closure failed.")

if __name__ == "__main__":
    asyncio.run(test_trading())
