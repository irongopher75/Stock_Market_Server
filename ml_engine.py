import yfinance as yf
import pandas as pd
import numpy as np
import config

class MarketAnalyzer:
    def __init__(self, symbol):
        self.symbol = symbol
        self.data = None

    async def fetch_data(self, period="1mo", interval="1h"):
        # 1. Resolve ticker from map or use direct symbol
        search_symbol = self.symbol.upper()
        search_symbol = config.TICKER_MAP.get(search_symbol, search_symbol)
        
        # 2. Apply default suffix if it's a plain equity ticker (no dot, no caret)
        if "." not in search_symbol and not search_symbol.startswith("^"):
            search_symbol = f"{search_symbol}{config.DEFAULT_TICKER_SUFFIX}"
            
        ticker = yf.Ticker(search_symbol)
        
        import asyncio
        self.data = await asyncio.to_thread(ticker.history, period=period, interval=interval)
        
        if self.data.empty:
            raise Exception(f"No data found for symbol {self.symbol} (Ticker: {search_symbol})")
            
        # --- HFT Algo 1.1: Real-Time Data Normalization ---
        # 1. Outlier Detection
        rolling_median = self.data['Close'].rolling(window=config.SMA_FAST).median()
        self.data['Close'] = np.where(
            (self.data['Close'] > rolling_median * 1.10) | (self.data['Close'] < rolling_median * 0.90),
            rolling_median,
            self.data['Close']
        ).astype(float)
        
        # 2. Gap Filling
        self.data.ffill(inplace=True)
        # --------------------------------------------------

    def calculate_atr(self, window=None):
        window = window or config.ATR_WINDOW
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
        gain = (delta.where(delta > 0, 0)).rolling(window=config.RSI_WINDOW).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=config.RSI_WINDOW).mean()
        rs = gain / loss
        self.data['RSI'] = 100 - (100 / (1 + rs))
        
        # SMAs
        self.data['SMA_20'] = close.rolling(window=config.SMA_FAST).mean()
        self.data['SMA_50'] = close.rolling(window=config.SMA_MEDIUM).mean()
        self.data['SMA_200'] = close.rolling(window=config.SMA_SLOW).mean()

        # --- HFT Algo 2.2: Adaptive MACD ---
        atr_pct = (self.data['ATR'] / close) * 100
        vol_ratio = atr_pct.iloc[-1]
        
        if vol_ratio > config.VOL_HIGH_THRESHOLD: # High Vol
            f, s, sig = 8, 17, 6
        elif vol_ratio < config.VOL_LOW_THRESHOLD: # Low Vol
            f, s, sig = 16, 35, 12
        else: # Normal
            f, s, sig = 12, 26, 9
            
        exp1 = close.ewm(span=f, adjust=False).mean()
        exp2 = close.ewm(span=s, adjust=False).mean()
        self.data['MACD'] = exp1 - exp2
        self.data['Signal_Line'] = self.data['MACD'].ewm(span=sig, adjust=False).mean()
        
        # --- HFT Algo 2.3: Dynamic Bollinger Bands ---
        std = close.rolling(window=config.SMA_FAST).std()
        if vol_ratio > config.VOL_VERY_HIGH: multiplier = 2.5
        elif vol_ratio < config.VOL_VERY_LOW: multiplier = 1.5
        else: multiplier = 2.0
        
        self.data['BB_Upper'] = self.data['SMA_20'] + (std * multiplier)
        self.data['BB_Lower'] = self.data['SMA_20'] - (std * multiplier)
        
        # --- HFT Algo 2.5: Volume Profile ---
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
        macd = last_row['MACD']
        signal = last_row['Signal_Line']
        bb_lower = last_row['BB_Lower']
        bb_upper = last_row['BB_Upper']
        volume = last_row['Volume']
        avg_volume = self.data['Volume'].tail(config.MOMENTUM_LOOKBACK).mean()
        
        score = 0
        reasons = []
        
        # --- HFT Strategy 3.1: Scalping Logic ---
        scalp_score = 0
        if rsi < 30: scalp_score += 2
        elif rsi > 70: scalp_score -= 2
        if macd > signal and prev_row['MACD'] <= prev_row['Signal_Line']: scalp_score += 2
        elif macd < signal and prev_row['MACD'] >= prev_row['Signal_Line']: scalp_score -= 2
        if volume > avg_volume * config.VOL_确认_RATIO:
            scalp_score *= 1.5
            reasons.append("Scalping: Volume spike detected.")

        # --- HFT Strategy 3.2: Momentum Breakout ---
        recent_high = self.data['High'].tail(config.MOMENTUM_LOOKBACK).max()
        if price > recent_high * config.MOMENTUM_PROXIMITY:
            reasons.append("Momentum: Price near local high.")
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
                reasons.append(f"Trend: Above Volume POC.")
            else:
                score -= 1
                reasons.append(f"Trend: Below Volume POC.")

        # Composite Scoring
        total_score = score + (scalp_score * 0.5)
        
        prediction = "NEUTRAL"
        confidence = 0.5
        suggested_strategy = "Waiting for clearer signals"
        
        if total_score >= config.BULLISH_SCORE_THRESHOLD:
            prediction = "BULLISH"
            confidence = min(0.6 + (total_score * 0.05), 0.95)
            suggested_strategy = "HFT High Confidence Bullish - Buy ITM Call (CE)"
        elif total_score >= config.MOD_BULLISH_THRESHOLD:
            prediction = "BULLISH"
            confidence = 0.65
            suggested_strategy = "HFT Moderate Bullish - Buy ATM Call (CE)"
        elif total_score <= config.BEARISH_SCORE_THRESHOLD:
            prediction = "BEARISH"
            confidence = min(0.6 + (abs(total_score) * 0.05), 0.95)
            suggested_strategy = "HFT High Confidence Bearish - Buy ITM Put (PE)"
        elif total_score <= config.MOD_BEARISH_THRESHOLD:
            prediction = "BEARISH"
            confidence = 0.65
            suggested_strategy = "HFT Moderate Bearish - Buy ATM Put (PE)"
            
        return self._sanitize({
            "prediction": prediction,
            "confidence": round(confidence, 2),
            "rsi": round(rsi, 2),
            "macd": round(macd, 4),
            "sma_20": round(last_row['SMA_20'], 2),
            "sma_50": round(last_row['SMA_50'], 2),
            "sma_200": round(last_row['SMA_200'], 2),
            "bb_upper": round(bb_upper, 2),
            "bb_lower": round(bb_lower, 2),
            "current_price": round(price, 2),
            "strategy": suggested_strategy,
            "reasoning": " | ".join(reasons) if reasons else "No dominant HFT signals detected.",
            "poc": round(self.poc_price, 2) if self.poc_price else None,
            "vol_ratio": round((last_row['ATR'] / price) * 100, 2)
        })

    def _sanitize(self, obj):
        if isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize(v) for v in obj]
        elif isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
            return None
        return obj

    def generate_payoff_graph(self, option_type, strike, premium=None):
        premium = premium or config.OPTION_PREMIUM_DEFAULT
        scan_range = config.OPTION_SCAN_RANGE
        spots = np.linspace(strike * (1 - scan_range), strike * (1 + scan_range), 20)
        payoffs = []
        for s in spots:
            if option_type == "CE":
                profit = max(0, s - strike) - premium
            else:
                profit = max(0, strike - s) - premium
            payoffs.append({"spot": round(s, 2), "profit": round(profit, 2)})
        return payoffs
