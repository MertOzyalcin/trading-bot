# ══════════════════════════════════════════════════════════════════════════════
# config.py — All settings in one place
# Change anything about the bot's behavior here
# ══════════════════════════════════════════════════════════════════════════════

from dotenv import load_dotenv
from zoneinfo import ZoneInfo
import os, pathlib

load_dotenv()

# ── API KEYS ───────────────────────────────────────────────────────────────────
API_KEY       = os.getenv("API_KEY")
SECRET        = os.getenv("SECRET_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_KEY")

# ── TRADING ────────────────────────────────────────────────────────────────────
WATCHLIST  = ["AAPL", "TSLA", "MSFT", "NVDA"]  # stocks to scan
RISK_PCT   = 0.02   # risk 2% of account balance per trade
STOP_PCT   = 0.05   # stop-loss: exit if price drops 5% below buy
PROFIT_PCT = 0.10   # take-profit: exit if price rises 10% above buy

# ── STRATEGY ───────────────────────────────────────────────────────────────────
RSI_PERIOD   = 14   # RSI lookback period (14 is the standard)
RSI_BUY      = 30   # buy signal when RSI drops below this
RSI_SELL     = 70   # sell signal when RSI rises above this
HISTORY_DAYS = 60   # days of price history to fetch for RSI

# ── SCHEDULE ───────────────────────────────────────────────────────────────────
# EDT season (Mar–Nov): 16:31 Istanbul
# EST season (Nov–Mar): change to 17:31
RUN_TIME = "16:31"

# ── SAFETY ─────────────────────────────────────────────────────────────────────
MARKET_FREEFALL_PCT  = -5.0   # block all trades if SPY down this % in 5 days
SINGLE_DAY_DROP_PCT  = -10.0  # skip stock if it dropped this % today
EARNINGS_DAYS_AHEAD  = 5      # skip stock if earnings within this many days
MARKET_OPEN_BUFFER   = 30     # skip first N minutes after market open (9:30 ET)
MARKET_CLOSE_BUFFER  = 30     # skip last N minutes before market close (4:00 ET)

# ── TIMEZONE ───────────────────────────────────────────────────────────────────
ET = ZoneInfo("America/New_York")   # US Eastern time for market hour checks

# ── FILES ──────────────────────────────────────────────────────────────────────
BASE_DIR   = pathlib.Path(__file__).parent
LOG_FILE   = BASE_DIR / "bot_log.csv"
CACHE_FILE = BASE_DIR / "skip_days_cache.json"