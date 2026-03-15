# ══════════════════════════════════════════════════════════════════════════════
# config.py — All settings in one place
# ══════════════════════════════════════════════════════════════════════════════

from dotenv import load_dotenv
from zoneinfo import ZoneInfo
import os, pathlib

load_dotenv()

# ── API KEYS ───────────────────────────────────────────────────────────────────
API_KEY       = os.getenv("API_KEY")
SECRET        = os.getenv("SECRET_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_KEY")

# ── TRADING MODE ───────────────────────────────────────────────────────────────
# PAPER_TRADING = True  → simulated money, safe to test (default)
# PAPER_TRADING = False → REAL money, only change after 3-6 months paper trading
PAPER_TRADING = True

# ── WATCHLIST ──────────────────────────────────────────────────────────────────
WATCHLIST = ["AAPL", "TSLA", "MSFT", "NVDA"]

# ── RISK MANAGEMENT ────────────────────────────────────────────────────────────
RISK_PCT   = 0.02   # risk 2% of account per trade
STOP_PCT   = 0.05   # stop-loss: exit if price drops 5% below buy
PROFIT_PCT = 0.10   # take-profit: exit if price rises 10% above buy

# ── RSI — DAILY ────────────────────────────────────────────────────────────────
RSI_PERIOD   = 14
RSI_BUY      = 30   # buy signal when daily RSI drops below this
RSI_SELL     = 70   # sell signal when daily RSI rises above this
HISTORY_DAYS = 60   # days of daily price history to fetch

# ── RSI — MULTI-TIMEFRAME ──────────────────────────────────────────────────────
MTF_WEEKLY_MAX  = 50    # weekly RSI must be below this
MTF_HOURLY_MAX  = 40    # hourly RSI must be below this
MTF_WEEKLY_DAYS = 365
MTF_HOURLY_BARS = 200

# ── MACD ───────────────────────────────────────────────────────────────────────
MACD_FAST           = 12
MACD_SLOW           = 26
MACD_SIGNAL         = 9
MACD_HISTOGRAM_BARS = 3   # histogram must rise for this many consecutive days

# ── SCHEDULE ───────────────────────────────────────────────────────────────────
# EDT (Mar–Nov): 16:31 Istanbul | EST (Nov–Mar): 17:31 Istanbul
RUN_TIME = "16:31"

# ── SAFETY ─────────────────────────────────────────────────────────────────────
MARKET_FREEFALL_PCT  = -5.0
SINGLE_DAY_DROP_PCT  = -10.0
EARNINGS_DAYS_AHEAD  = 5
MARKET_OPEN_BUFFER   = 30
MARKET_CLOSE_BUFFER  = 30

# ── TIMEZONE ───────────────────────────────────────────────────────────────────
ET = ZoneInfo("America/New_York")

# ── FILES ──────────────────────────────────────────────────────────────────────
BASE_DIR   = pathlib.Path(__file__).parent
LOG_FILE   = BASE_DIR / "bot_log.csv"
CACHE_FILE = BASE_DIR / "skip_days_cache.json"