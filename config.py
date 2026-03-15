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
WATCHLIST  = ["AAPL", "TSLA", "MSFT", "NVDA"]
RISK_PCT   = 0.02   # risk 2% of account balance per trade
STOP_PCT   = 0.05   # stop-loss: exit if price drops 5% below buy
PROFIT_PCT = 0.10   # take-profit: exit if price rises 10% above buy

# ── RSI — DAILY (primary signal) ───────────────────────────────────────────────
RSI_PERIOD   = 14   # RSI lookback period (14 is standard)
RSI_BUY      = 30   # daily RSI must be BELOW this → oversold → consider buying
RSI_SELL     = 70   # daily RSI must be ABOVE this → overbought → consider selling
HISTORY_DAYS = 60   # days of daily price history to fetch

# ── RSI — MULTI-TIMEFRAME FILTERS ─────────────────────────────────────────────
# All three timeframes must agree before placing any BUY order.
# This dramatically reduces false signals by requiring confluence.
#
# The logic works like a 3-step gate:
#
#   Gate 1 — Daily RSI < 30
#     "Is this stock oversold on the daily chart?"
#     This is your original signal — nothing changes here.
#
#   Gate 2 — Weekly RSI < 50
#     "Is the big weekly trend neutral or bearish?"
#     If weekly RSI is above 50, the stock is in a strong uptrend
#     and the daily dip is just a small pullback — not a real oversell.
#     We want the weekly to be weak so we're not fighting the big trend.
#
#   Gate 3 — Hourly RSI < 40
#     "Is right now actually a good entry point intraday?"
#     Even if daily says oversold, we want the hourly to also be weak
#     so we're not buying right at a short-term bounce peak.
#
#   Only if ALL THREE pass → ask Claude → place bracket order
#
MTF_WEEKLY_MAX  = 50    # weekly RSI must be below this
MTF_HOURLY_MAX  = 40    # hourly RSI must be below this
MTF_WEEKLY_DAYS = 365   # 1 year of data to calculate weekly RSI accurately
MTF_HOURLY_BARS = 200   # number of hourly bars to fetch (covers ~5-6 weeks)

# ── SCHEDULE ───────────────────────────────────────────────────────────────────
# EDT season (Mar–Nov): 16:31 Istanbul
# EST season (Nov–Mar): change to 17:31
RUN_TIME = "16:31"

# ── SAFETY ─────────────────────────────────────────────────────────────────────
MARKET_FREEFALL_PCT  = -5.0   # block all trades if SPY down this % in 5 days
SINGLE_DAY_DROP_PCT  = -10.0  # skip stock if it dropped this % today
EARNINGS_DAYS_AHEAD  = 5      # skip stock if earnings within this many days
MARKET_OPEN_BUFFER   = 30     # skip first N minutes after market open
MARKET_CLOSE_BUFFER  = 30     # skip last N minutes before market close

# ── TIMEZONE ───────────────────────────────────────────────────────────────────
ET = ZoneInfo("America/New_York")

# ── FILES ──────────────────────────────────────────────────────────────────────
BASE_DIR   = pathlib.Path(__file__).parent
LOG_FILE   = BASE_DIR / "bot_log.csv"
CACHE_FILE = BASE_DIR / "skip_days_cache.json"