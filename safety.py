# ══════════════════════════════════════════════════════════════════════════════
# safety.py — All safety checks
# Every check returns (is_safe: bool, reason: str)
# True = safe to trade, False = block this trade with the given reason
# ══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timedelta, date
from config import (
    ET, MARKET_FREEFALL_PCT, SINGLE_DAY_DROP_PCT,
    EARNINGS_DAYS_AHEAD, MARKET_OPEN_BUFFER, MARKET_CLOSE_BUFFER
)
from skip_days import should_skip_today
import yfinance as yf
import pandas as pd


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CHECKS — apply to ALL stocks
# If any of these fail, the entire scan is blocked for the day
# ══════════════════════════════════════════════════════════════════════════════

def check_skip_date():
    """
    Uses skip_days.py to auto-detect:
      - NYSE market holidays (exchange closed)
      - Fed FOMC rate announcement days
      - Major economic events (CPI, Jobs Report, GDP)
    """
    skip, reason = should_skip_today()
    # should_skip_today() returns True = should skip
    # we flip it: True = safe, False = blocked
    return (not skip), reason


def check_market_hours():
    """
    Blocks trading in the first and last 30 minutes of the session.

    Why: The market open (9:30–10:00 ET) and close (3:30–4:00 ET) are
    the most volatile periods of the day. Prices spike and crash without
    clear reason. Your bot runs at 9:31 AM ET — this is a known risk zone.

    Safe trading window: 10:00 AM – 3:30 PM US Eastern.
    """
    now_et       = datetime.now(ET)
    open_buffer  = now_et.replace(hour=9,  minute=30, second=0) + timedelta(minutes=MARKET_OPEN_BUFFER)
    close_buffer = now_et.replace(hour=16, minute=0,  second=0) - timedelta(minutes=MARKET_CLOSE_BUFFER)

    if now_et < open_buffer:
        return False, f"⏰ Too early — waiting until {open_buffer.strftime('%H:%M')} ET"
    if now_et > close_buffer:
        return False, f"⏰ Too late — last safe time is {close_buffer.strftime('%H:%M')} ET"
    return True, ""


def check_market_freefall():
    """
    Blocks all trading if SPY (S&P 500 ETF) is down more than 5% in 5 days.

    Why: When the whole market is falling hard, individual stock RSI signals
    become unreliable. Everything falls together in a crash regardless of
    technicals. Better to sit out and wait for stabilization.
    """
    try:
        spy = yf.download("SPY", period="10d", auto_adjust=True, progress=False)
        spy.columns = [c[0] if isinstance(c, tuple) else c for c in spy.columns]
        closes      = spy["Close"].dropna()

        if len(closes) < 5:
            return True, ""   # not enough data — don't block

        change_pct = ((closes.iloc[-1] - closes.iloc[-5]) / closes.iloc[-5]) * 100
        print(f"  📊 SPY 5-day change: {change_pct:.1f}%")

        if change_pct <= MARKET_FREEFALL_PCT:
            return False, f"📉 Market freefall — SPY down {change_pct:.1f}% in 5 days"
        return True, ""

    except Exception as e:
        print(f"  ⚠️ SPY check failed: {e} — skipping freefall check")
        return True, ""   # if check fails, don't block trading


def run_global_safety_checks():
    """
    Runs all global checks in order.
    Returns (is_safe: bool, reason: str).
    Stops at the first failure — no need to check the rest.
    """
    checks = [
        ("Skip Date",    check_skip_date),
        ("Market Hours", check_market_hours),
        ("SPY Freefall", check_market_freefall),
    ]

    for name, check_fn in checks:
        is_safe, reason = check_fn()
        if not is_safe:
            return False, reason

    return True, ""


# ══════════════════════════════════════════════════════════════════════════════
# STOCK-LEVEL CHECKS — apply to ONE stock before buying it
# ══════════════════════════════════════════════════════════════════════════════

def check_single_day_crash(closes):
    """
    Skips a stock if it dropped more than 10% today vs yesterday.

    Why: A 10%+ single-day drop almost always means bad news —
    a lawsuit, earnings miss, CEO resignation, or scandal.
    RSI going oversold because of bad news is NOT a buying opportunity.
    RSI oversold + bad news = dangerous combination.
    """
    if len(closes) < 2:
        return True, ""

    today_close     = float(closes.iloc[-1])
    yesterday_close = float(closes.iloc[-2])
    change_pct      = ((today_close - yesterday_close) / yesterday_close) * 100

    if change_pct <= SINGLE_DAY_DROP_PCT:
        return False, f"💥 Single-day crash: down {change_pct:.1f}% today"
    return True, ""


def check_earnings(symbol):
    """
    Skips a stock if earnings are within EARNINGS_DAYS_AHEAD days.

    Why: Earnings reports cause ±20% price moves in minutes.
    RSI, MACD, and every other technical indicator becomes meaningless
    next to a surprise earnings number. Always skip earnings week.
    """
    try:
        ticker = yf.Ticker(symbol)
        cal    = ticker.calendar

        earnings_date = None
        if cal is not None:
            for key in ["Earnings Date", "earningsDate", "Earnings"]:
                if key in cal:
                    val = cal[key]
                    if isinstance(val, (list, pd.Index)) and len(val) > 0:
                        earnings_date = pd.Timestamp(val[0]).date()
                    elif hasattr(val, "date"):
                        earnings_date = val.date()
                    break

        if earnings_date:
            days_away = (earnings_date - date.today()).days
            if 0 <= days_away <= EARNINGS_DAYS_AHEAD:
                return False, f"📊 {symbol} earnings in {days_away} day(s) ({earnings_date})"

        return True, ""

    except Exception as e:
        print(f"  ⚠️ Earnings check failed for {symbol}: {e}")
        return True, ""


def run_stock_safety_checks(symbol, closes):
    """
    Runs all stock-level checks for a single symbol.
    Returns (is_safe: bool, reason: str).
    """
    checks = [
        ("Single Day Crash", lambda: check_single_day_crash(closes)),
        ("Earnings",         lambda: check_earnings(symbol)),
    ]

    for name, check_fn in checks:
        is_safe, reason = check_fn()
        if not is_safe:
            return False, reason

    return True, ""