# ══════════════════════════════════════════════════════════════════════════════
# strategy.py — Trading strategy logic
# RSI signal (daily + weekly + hourly) + Claude AI analysis
# ══════════════════════════════════════════════════════════════════════════════

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from config import (
    API_KEY, SECRET, ANTHROPIC_KEY,
    RSI_PERIOD, RSI_BUY, RSI_SELL, HISTORY_DAYS,
    MTF_WEEKLY_MAX, MTF_HOURLY_MAX,
    MTF_WEEKLY_DAYS, MTF_HOURLY_BARS
)
import anthropic
import pandas as pd
import ta


# ── CLIENTS ────────────────────────────────────────────────────────────────────
data_client   = StockHistoricalDataClient(API_KEY, SECRET)
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)


# ══════════════════════════════════════════════════════════════════════════════
# PRICE DATA FETCHERS
# ══════════════════════════════════════════════════════════════════════════════

def get_closes(symbol):
    """
    Fetches daily closing prices for RSI calculation.
    Returns a pandas Series.
    """
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=HISTORY_DAYS)
    )
    bars = data_client.get_stock_bars(req).df
    return bars["close"]


def get_weekly_closes(symbol):
    """
    Fetches weekly closing prices for the weekly RSI filter.

    Why weekly: Weekly RSI tells you the big picture trend.
    A daily oversell during a strong weekly uptrend is just a dip —
    not a genuine reversal. We want to see weekly RSI below 50,
    meaning the big trend is neutral or bearish, before buying.

    Returns a pandas Series of weekly closes.
    """
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Week,
        start=datetime.now() - timedelta(days=MTF_WEEKLY_DAYS)
    )
    bars = data_client.get_stock_bars(req).df
    return bars["close"]


def get_hourly_closes(symbol):
    """
    Fetches hourly closing prices for the hourly RSI filter.

    Why hourly: Even if the daily says oversold, we want the hourly
    to also be weak. This confirms we're not buying right at a
    short-term intraday bounce — we want the hourly momentum
    pointing down too so our entry timing is better.

    Returns a pandas Series of hourly closes.
    """
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Hour,
        start=datetime.now() - timedelta(days=30)   # 30 days of hourly data
    )
    bars = data_client.get_stock_bars(req).df
    # Take the most recent MTF_HOURLY_BARS bars only
    return bars["close"].tail(MTF_HOURLY_BARS)


def calculate_rsi(closes, period=None):
    """
    Calculates RSI for any series of closes.
    Returns the most recent RSI value as a float.
    """
    if period is None:
        period = RSI_PERIOD
    return float(ta.momentum.RSIIndicator(closes, period).rsi().iloc[-1])


# ══════════════════════════════════════════════════════════════════════════════
# DAILY SIGNAL (primary — same as before)
# ══════════════════════════════════════════════════════════════════════════════

def get_signal(closes):
    """
    Calculates daily RSI and returns the primary signal.

    RSI < 30  → BUY  (oversold)
    RSI > 70  → SELL (overbought)
    RSI 30-70 → HOLD (neutral)

    Returns (signal: str, rsi_value: float)
    """
    rsi = calculate_rsi(closes)
    print(f"  Daily  RSI: {rsi:.1f}", end="")

    if rsi < RSI_BUY:
        print(f"  ← oversold ✅")
        return "BUY", rsi
    elif rsi > RSI_SELL:
        print(f"  ← overbought")
        return "SELL", rsi
    else:
        print()
        return "HOLD", rsi


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-TIMEFRAME FILTER
# ══════════════════════════════════════════════════════════════════════════════

def passes_mtf_filter(symbol):
    """
    Runs the weekly and hourly RSI checks.
    Both must pass for the trade to proceed.

    Gate 2 — Weekly RSI < MTF_WEEKLY_MAX (50)
      Ensures we're not buying into a strong weekly uptrend.
      Weekly RSI above 50 = stock still has bullish momentum on the big chart.
      We want weekly RSI below 50 = big trend is neutral or tired.

    Gate 3 — Hourly RSI < MTF_HOURLY_MAX (40)
      Ensures the short-term entry timing is right.
      Hourly RSI below 40 = stock is also weak intraday.
      If hourly RSI is 65, the stock is bouncing right now — bad entry timing.

    Returns (passed: bool, reason: str)
    """

    # ── GATE 2: WEEKLY RSI ─────────────────────────────────────────────────────
    try:
        weekly_closes = get_weekly_closes(symbol)

        if len(weekly_closes) < RSI_PERIOD + 5:
            # Not enough weekly bars to calculate RSI reliably
            print(f"  Weekly RSI: ⚠️ Not enough data — skipping weekly filter")
        else:
            weekly_rsi = calculate_rsi(weekly_closes)
            status     = "✅" if weekly_rsi < MTF_WEEKLY_MAX else "❌"
            print(f"  Weekly RSI: {weekly_rsi:.1f}  (must be < {MTF_WEEKLY_MAX}) {status}")

            if weekly_rsi >= MTF_WEEKLY_MAX:
                return False, (
                    f"Weekly RSI {weekly_rsi:.1f} ≥ {MTF_WEEKLY_MAX} — "
                    f"big trend still has upward momentum, daily dip is just a pullback"
                )

    except Exception as e:
        print(f"  Weekly RSI: ⚠️ Failed ({e}) — skipping weekly filter")

    # ── GATE 3: HOURLY RSI ─────────────────────────────────────────────────────
    try:
        hourly_closes = get_hourly_closes(symbol)

        if len(hourly_closes) < RSI_PERIOD + 5:
            print(f"  Hourly RSI: ⚠️ Not enough data — skipping hourly filter")
        else:
            hourly_rsi = calculate_rsi(hourly_closes)
            status     = "✅" if hourly_rsi < MTF_HOURLY_MAX else "❌"
            print(f"  Hourly RSI: {hourly_rsi:.1f}  (must be < {MTF_HOURLY_MAX}) {status}")

            if hourly_rsi >= MTF_HOURLY_MAX:
                return False, (
                    f"Hourly RSI {hourly_rsi:.1f} ≥ {MTF_HOURLY_MAX} — "
                    f"short-term momentum not weak enough, wait for better entry"
                )

    except Exception as e:
        print(f"  Hourly RSI: ⚠️ Failed ({e}) — skipping hourly filter")

    # All gates passed
    return True, ""


# ══════════════════════════════════════════════════════════════════════════════
# CLAUDE AI ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def claude_approves(symbol, rsi, closes):
    """
    Asks Claude to evaluate the trade after all RSI filters have passed.
    At this point we know daily + weekly + hourly RSI all agree —
    Claude adds qualitative judgment about price action patterns.

    Returns (approved: bool, response_text: str)
    """
    recent_prices = [round(float(p), 2) for p in closes.tail(10).tolist()]
    current_price = recent_prices[-1]

    prompt = f"""You are a cautious trading assistant evaluating a stock trade.

Stock: {symbol}
Current Price: ${current_price}
Daily RSI (14-day): {rsi:.1f}
Last 10 daily closing prices: {recent_prices}

This trade has already passed a multi-timeframe RSI filter:
- Daily RSI is below 30 (oversold)
- Weekly RSI is below 50 (big trend is neutral)
- Hourly RSI is below 40 (short-term also weak)

All three timeframes agree this stock is weak.

Your job is to make the final qualitative judgment:
1. Does the price action look like a normal oversell or a fundamental breakdown?
2. Is the decline gradual (healthy) or a sharp single crash (news-driven)?
3. Given that all timeframes agree, does this look like a good risk/reward entry?

Respond with ONLY:
- First line: APPROVE or REJECT
- Second line: One sentence explaining why (max 20 words)

Be conservative but remember — all three RSI timeframes already agree."""

    message = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()
    print(f"  🤖 Claude: {response_text.replace(chr(10), ' | ')}")
    return response_text.upper().startswith("APPROVE"), response_text