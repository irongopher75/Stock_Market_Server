import os
import json
from dotenv import load_dotenv

load_dotenv()

# --- Symbol & Ticker Mapping ---
TICKER_MAP_FILE = os.path.join(os.path.dirname(__file__), "data", "ticker_mappings.json")
DEFAULT_TICKER_SUFFIX = os.getenv("DEFAULT_TICKER_SUFFIX", ".NS")

def load_ticker_map():
    if os.path.exists(TICKER_MAP_FILE):
        try:
            with open(TICKER_MAP_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

TICKER_MAP = load_ticker_map()

# --- System Constants ---
DEDUPLICATION_WINDOW_MINS = int(os.getenv("DEDUPLICATION_WINDOW_MINS", 15))

# --- Financial Defaults ---
INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", 1000000.0))
DEFAULT_SLIPPAGE = float(os.getenv("DEFAULT_SLIPPAGE", 0.0001))

# --- Engine Defaults ---
DEFAULT_WIN_RATE = float(os.getenv("DEFAULT_WIN_RATE", 0.55))
DEFAULT_AVG_WIN = float(os.getenv("DEFAULT_AVG_WIN", 1.5))
DEFAULT_AVG_LOSS = float(os.getenv("DEFAULT_AVG_LOSS", 1.0))

# --- Technical Indicator Windows ---
RSI_WINDOW = int(os.getenv("RSI_WINDOW", 14))
SMA_FAST = int(os.getenv("SMA_FAST", 20))
SMA_MEDIUM = int(os.getenv("SMA_MEDIUM", 50))
SMA_SLOW = int(os.getenv("SMA_SLOW", 200))
ATR_WINDOW = int(os.getenv("ATR_WINDOW", 14))

# --- Prediction Thresholds ---
BULLISH_SCORE_THRESHOLD = float(os.getenv("BULLISH_SCORE_THRESHOLD", 3.0))
BEARISH_SCORE_THRESHOLD = float(os.getenv("BEARISH_SCORE_THRESHOLD", -3.0))
MOD_BULLISH_THRESHOLD = float(os.getenv("MOD_BULLISH_THRESHOLD", 1.0))
MOD_BEARISH_THRESHOLD = float(os.getenv("MOD_BEARISH_THRESHOLD", -1.0))

# --- Volatility Adaptation (HFT Algos) ---
VOL_HIGH_THRESHOLD = float(os.getenv("VOL_HIGH_THRESHOLD", 3.0))
VOL_LOW_THRESHOLD = float(os.getenv("VOL_LOW_THRESHOLD", 1.0))
VOL_VERY_HIGH = float(os.getenv("VOL_VERY_HIGH", 4.0))
VOL_VERY_LOW = float(os.getenv("VOL_VERY_LOW", 1.5))

# --- Strategy Factors ---
VOL_确认_RATIO = float(os.getenv("VOL_CONFIRM_RATIO", 1.5)) # Spike factor
MOMENTUM_LOOKBACK = int(os.getenv("MOMENTUM_LOOKBACK", 20))
MOMENTUM_PROXIMITY = float(os.getenv("MOMENTUM_PROXIMITY", 0.995))

# --- Options Simulation ---
OPTION_PREMIUM_DEFAULT = float(os.getenv("OPTION_PREMIUM_DEFAULT", 100))
OPTION_SCAN_RANGE = float(os.getenv("OPTION_SCAN_RANGE", 0.10)) # 10% each side
