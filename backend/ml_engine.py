import pandas as pd
import numpy as np
from . import data_manager

class MarketAnalyzer:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data = None
        
    def fetch_data(self):
        self.data = data_manager.fetch_stock_history(self.symbol)
        
    def calculate_indicators(self):
        if self.data is None:
            self.fetch_data()
            
        df = self.data.copy()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # SMA
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        self.data = df
        return df
    
    def predict_direction(self):
        """
        Simple Logic-based prediction for Prototype.
        Replace with ML Model (RandomForest/LSTM) later.
        """
        if self.data is None:
            self.calculate_indicators()
            
        latest = self.data.iloc[-1]
        rsi = latest['RSI']
        close = latest['Close']
        sma_50 = latest['SMA_50']
        
        prediction = "NEUTRAL"
        confidence = 0.5
        strategy = "Wait for clear signal"
        
        # Simple Logic
        if rsi < 30 and close > sma_50:
            prediction = "BULLISH"
            confidence = 0.8
            strategy = "Buy CE (Call Option)"
        elif rsi > 70 and close < sma_50:
            prediction = "BEARISH"
            confidence = 0.8
            strategy = "Buy PE (Put Option)"
        elif close > sma_50:
            prediction = "BULLISH"
            confidence = 0.6
            strategy = "Buy CE"
            
        return {
            "symbol": self.symbol,
            "current_price": close,
            "prediction": prediction,
            "confidence": confidence,
            "strategy": strategy,
            "rsi": rsi
        }

    def generate_payoff_graph(self, option_type: str, strike_price: float, premium: float):
        """
        Generates (x, y) coordinates for the payoff graph.
        """
        spot_prices = np.linspace(strike_price * 0.9, strike_price * 1.1, 50)
        payoffs = []
        
        for spot in spot_prices:
            if option_type == "CE":
                profit = max(0, spot - strike_price) - premium
            else:
                profit = max(0, strike_price - spot) - premium
            payoffs.append({"spot": round(spot, 2), "profit": round(profit, 2)})
            
        return payoffs
