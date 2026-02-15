import yfinance as yf
import pandas as pd
import numpy as np

class MarketAnalyzer:
    def __init__(self, symbol):
        self.symbol = symbol
        self.data = None

    def fetch_data(self, period="1mo", interval="1h"):
        # For NIFTY/BANKNIFTY use ^NSEI and ^NSEBANK
        search_symbol = self.symbol.upper()
        if search_symbol == "NIFTY":
            search_symbol = "^NSEI"
        elif search_symbol == "BANKNIFTY":
            search_symbol = "^NSEBANK"
        elif not search_symbol.endswith(".NS") and not search_symbol.startswith("^"):
            search_symbol = f"{search_symbol}.NS"
            
        ticker = yf.Ticker(search_symbol)
        self.data = ticker.history(period=period, interval=interval)
        if self.data.empty:
            raise Exception(f"No data found for symbol {self.symbol}")
            
        # --- HFT Algo 1.1: Real-Time Data Normalization ---
        # 1. Outlier Detection (Price change > 10% in one step is often an error in low-frequency data)
        # However, for HFT we use rolling median for sanity
        rolling_median = self.data['Close'].rolling(window=20).median()
        self.data['Close'] = np.where(
            (self.data['Close'] > rolling_median * 1.10) | (self.data['Close'] < rolling_median * 0.90),
            rolling_median,
            self.data['Close']
        ).astype(float)
        
        # 2. Gap Filling
        self.data.ffill(inplace=True)
        # --------------------------------------------------

    def calculate_atr(self, window=14):
        high_low = self.data['High'] - self.data['Low']
        high_close = np.abs(self.data['High'] - self.data['Close'].shift())
        low_close = np.abs(self.data['Low'] - self.data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        return true_range.rolling(window=window).mean()

    def calculate_indicators(self):
        close = self.data['Close']
        self.data['ATR'] = self.calculate_atr()
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        self.data['RSI'] = 100 - (100 / (1 + rs))
        
        # SMAs
        self.data['SMA_20'] = close.rolling(window=20).mean()
        self.data['SMA_50'] = close.rolling(window=50).mean()
        self.data['SMA_200'] = close.rolling(window=200).mean()

        # --- HFT Algo 2.2: Adaptive MACD ---
        # Adjust periods based on ATR percentage
        atr_pct = (self.data['ATR'] / close) * 100
        vol_ratio = atr_pct.iloc[-1]
        
        if vol_ratio > 3.0: # High Vol
            f, s, sig = 8, 17, 6
        elif vol_ratio < 1.0: # Low Vol
            f, s, sig = 16, 35, 12
        else: # Normal
            f, s, sig = 12, 26, 9
            
        exp1 = close.ewm(span=f, adjust=False).mean()
        exp2 = close.ewm(span=s, adjust=False).mean()
        self.data['MACD'] = exp1 - exp2
        self.data['Signal_Line'] = self.data['MACD'].ewm(span=sig, adjust=False).mean()
        
        # --- HFT Algo 2.3: Dynamic Bollinger Bands ---
        std = close.rolling(window=20).std()
        # Multiplier adapts to volatility state
        if vol_ratio > 4.0: multiplier = 2.5
        elif vol_ratio < 1.5: multiplier = 1.5
        else: multiplier = 2.0
        
        self.data['BB_Upper'] = self.data['SMA_20'] + (std * multiplier)
        self.data['BB_Lower'] = self.data['SMA_20'] - (std * multiplier)
        
        # --- HFT Algo 2.5: Volume Profile (Basic POC/HVN) ---
        # Divide recent data into bins
        recent_data = self.data.tail(100)
        p_min, p_max = recent_data['Close'].min(), recent_data['Close'].max()
        if p_max > p_min:
            bins = np.linspace(p_min, p_max, 20)
            v_profile = recent_data.groupby(pd.cut(recent_data['Close'], bins))['Volume'].sum()
            self.poc_price = (v_profile.idxmax().left + v_profile.idxmax().right) / 2 if not v_profile.empty else None
        else:
            self.poc_price = p_min
        
    def predict_direction(self, strategy_type="ensemble"):
        self.calculate_indicators()
        last_row = self.data.iloc[-1]
        prev_row = self.data.iloc[-2]
        
        rsi = last_row['RSI']
        price = last_row['Close']
        sma_50 = last_row['SMA_50']
        macd = last_row['MACD']
        signal = last_row['Signal_Line']
        bb_lower = last_row['BB_Lower']
        bb_upper = last_row['BB_Upper']
        volume = last_row['Volume']
        avg_volume = self.data['Volume'].tail(20).mean()
        
        score = 0
        reasons = []
        hft_strategy = "NEUTRAL"
        
        # --- HFT Strategy 3.1: Scalping Logic ---
        scalp_score = 0
        if rsi < 30: scalp_score += 2
        elif rsi > 70: scalp_score -= 2
        if macd > signal and prev_row['MACD'] <= prev_row['Signal_Line']: scalp_score += 2
        elif macd < signal and prev_row['MACD'] >= prev_row['Signal_Line']: scalp_score -= 2
        if volume > avg_volume * 1.5:
            scalp_score *= 1.5 # Volume confirmation
            reasons.append("Scalping: Volume spike detected.")

        # --- HFT Strategy 3.2: Momentum Breakout ---
        recent_high = self.data['High'].tail(20).max()
        recent_low = self.data['Low'].tail(20).min()
        if price > recent_high * 0.995:
            reasons.append("Momentum: Price near 20-period high.")
            if volume > avg_volume * 1.3:
                score += 2
                reasons.append("Momentum: Breakout confirmed by volume.")

        # --- HFT Strategy 3.3: Mean Reversion ---
        if price < bb_lower and rsi < 35:
            score += 2
            reasons.append("Mean Reversion: Price below lower BB with oversold RSI.")
        elif price > bb_upper and rsi > 65:
            score -= 2
            reasons.append("Mean Reversion: Price above upper BB with overbought RSI.")

        # POC Context
        if self.poc_price:
            if price > self.poc_price:
                score += 1
                reasons.append(f"Trend: Above Volume POC ({round(self.poc_price, 2)}).")
            else:
                score -= 1
                reasons.append(f"Trend: Below Volume POC ({round(self.poc_price, 2)}).")

        # Composite Scoring
        total_score = score + (scalp_score * 0.5)
        
        prediction = "NEUTRAL"
        confidence = 0.5
        suggested_strategy = "Waiting for clearer signals"
        
        if total_score >= 3:
            prediction = "BULLISH"
            confidence = min(0.6 + (total_score * 0.05), 0.95)
            suggested_strategy = "HFT High Confidence Bullish - Buy ITM Call (CE)"
        elif total_score >= 1:
            prediction = "BULLISH"
            confidence = 0.65
            suggested_strategy = "HFT Moderate Bullish - Buy ATM Call (CE)"
        elif total_score <= -3:
            prediction = "BEARISH"
            confidence = min(0.6 + (abs(total_score) * 0.05), 0.95)
            suggested_strategy = "HFT High Confidence Bearish - Buy ITM Put (PE)"
        elif total_score <= -1:
            prediction = "BEARISH"
            confidence = 0.65
            suggested_strategy = "HFT Moderate Bearish - Buy ATM Put (PE)"
            
        return {
            "prediction": prediction,
            "confidence": round(confidence, 2),
            "rsi": round(rsi, 2),
            "macd": round(macd, 4),
            "sma_50": round(sma_50, 2),
            "current_price": round(price, 2),
            "strategy": suggested_strategy,
            "reasoning": " | ".join(reasons) if reasons else "No dominant HFT signals detected.",
            "poc": round(self.poc_price, 2) if self.poc_price else None
        }

    def generate_payoff_graph(self, option_type, strike, premium):
        spots = np.linspace(strike * 0.9, strike * 1.1, 20)
        payoffs = []
        for s in spots:
            if option_type == "CE":
                profit = max(0, s - strike) - premium
            else:
                profit = max(0, strike - s) - premium
            payoffs.append({"spot": round(s, 2), "profit": round(profit, 2)})
        return payoffs
