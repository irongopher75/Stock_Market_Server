from app.db import models, recovery
from app.core import config
from app.services.execution_engine import ExecutionEngine
from datetime import datetime, timezone
from app.core.constants import OrderSide, OrderStatus
import logging

logger = logging.getLogger(__name__)

class TradingManager:
    def __init__(self):
        self.executor = ExecutionEngine(simulation_mode=True)

    async def open_position(self, user_id: str, symbol: str, side: OrderSide, price: float, quantity: float, strategy: str = "MANUAL"):
        """Executes an entry via SOR and persists the trade."""
        # 1. Route via SOR
        execution = self.executor.route_order(symbol, quantity, side, price)
        
        if execution["status"] == OrderStatus.FILLED:
            # 2. Persist to DB
            trade = models.Trade(
                user_id=user_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=execution["price"],
                status=OrderStatus.OPEN,
                strategy=strategy
            )
            await trade.insert()
            
            # 3. Update System State (Disaster Recovery)
            state = await recovery.get_state(user_id)
            positions = state.active_positions if state else {}
            positions[symbol] = {
                "id": str(trade.id),
                "quantity": quantity,
                "price": execution["price"],
                "side": side
            }
            
            balance = state.last_known_balance if state else config.INITIAL_BALANCE
            await recovery.save_state(user_id, balance, positions)
            
            logger.info(f"TRADE OPENED: {side} {quantity} {symbol} for User {user_id}")
            return trade
        return None

    async def close_position(self, user_id: str, trade_id: str, current_price: float = None):
        """Closes an active position by ID and calculates final P&L."""
        from beanie import PydanticObjectId
        
        try:
            # Handle potential string to ObjectId conversion
            if isinstance(trade_id, str):
                obj_id = PydanticObjectId(trade_id)
            else:
                obj_id = trade_id
        except Exception as e:
            logger.error(f"Invalid Trade ID format: {trade_id} - {str(e)}")
            return None

        trade = await models.Trade.find_one(
            models.Trade.id == obj_id,
            models.Trade.user_id == user_id,
            models.Trade.status == OrderStatus.OPEN
        )
        
        if not trade:
            # Check if it exists but is closed
            any_trade = await models.Trade.find_one(models.Trade.id == obj_id, models.Trade.user_id == user_id)
            if any_trade:
                logger.warning(f"Trade {trade_id} found but status is {any_trade.status}")
            else:
                logger.warning(f"Trade {trade_id} not found for user {user_id}")
            return None

        # 1. Fetch current price if not provided
        if not current_price:
            import yfinance as yf
            search_symbol = trade.symbol.upper()
            if search_symbol == "NIFTY": search_symbol = "^NSEI"
            elif search_symbol == "BANKNIFTY": search_symbol = "^NSEBANK"
            else: search_symbol = f"{search_symbol}.NS"
            
            ticker = yf.Ticker(search_symbol)
            current_price = ticker.history(period="1d")['Close'].iloc[-1]

        # 2. Route via SOR (Simulation)
        exit_side = OrderSide.SELL if trade.side == OrderSide.BUY else OrderSide.BUY
        execution = self.executor.route_order(trade.symbol, trade.quantity, exit_side, current_price)
        
        if execution["status"] == OrderStatus.FILLED:
            # 3. Update Trade record
            trade.exit_price = execution["price"]
            trade.status = OrderStatus.CLOSED
            trade.exit_timestamp = datetime.now(timezone.utc)
            
            # Profit Calculation
            if trade.side == OrderSide.BUY:
                trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
            else:
                trade.pnl = (trade.entry_price - trade.exit_price) * trade.quantity
                
            await trade.save()
            
            # 4. Update System State (Disaster Recovery Update)
            state = await recovery.get_state(user_id)
            if state and trade.symbol in state.active_positions:
                # Only remove if it's the exact position (DR usually stores by symbol, 
                # but we'll prune if the ID matches)
                if state.active_positions[trade.symbol].get("id") == trade_id:
                    del state.active_positions[trade.symbol]
                
                new_balance = state.last_known_balance + trade.pnl
                await recovery.save_state(user_id, new_balance, state.active_positions)
            
            logger.info(f"TRADE CLOSED: {trade.symbol} ID: {trade_id} P&L: {trade.pnl:.2f}")
            return trade
        return None
