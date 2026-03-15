# ══════════════════════════════════════════════════════════════════════════════
# strategy.py — Trading strategy logic
# RSI signal calculation + Claude AI analysis
# ══════════════════════════════════════════════════════════════════════════════

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from config import (
    API_KEY, SECRET, ANTHROPIC_KEY,
    RSI_PERIOD, RSI_BUY, RSI_SELL, HISTORY_DAYS
)
import anthropic
import ta


# ── CLIENTS ────────────────────────────────────────────────────────────────────
data_client   = StockHistoricalDataClient(API_KEY, SECRET)
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)


def get_closes(symbol):
    """
    Fetches last HISTORY_DAYS days of daily closing prices from Alpaca.
    Returns a pandas Series of closing prices.
    """
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=HISTORY_DAYS)
    )
    bars = data_client.get_stock_bars(req).df
    return bars["close"]


def get_signal(closes):
    """
    Calculates RSI and returns a trading signal.

    RSI below RSI_BUY (30)  → BUY  (stock is oversold, possible rebound)
    RSI above RSI_SELL (70) → SELL (stock is overbought, possible pullback)
    RSI between 30–70       → HOLD (neutral, no clear signal)

    Returns (signal: str, rsi_value: float)
    """
    rsi = ta.momentum.RSIIndicator(closes, RSI_PERIOD).rsi().iloc[-1]
    print(f"  RSI: {rsi:.1f}")

    if rsi < RSI_BUY:    return "BUY",  rsi
    elif rsi > RSI_SELL: return "SELL", rsi
    else:                return "HOLD", rsi


def claude_approves(symbol, rsi, closes):
    """
    Asks Claude to evaluate a potential trade before placing it.
    Sends the last 10 closing prices + RSI so Claude can see the recent trend.

    Claude looks for:
    - Is this a normal oversell or a news-driven crash?
    - Is the price declining steadily or bouncing?
    - Does this look like a genuine rebound opportunity?

    Returns (approved: bool, response_text: str)
    """
    recent_prices = [round(float(p), 2) for p in closes.tail(10).tolist()]
    current_price = recent_prices[-1]

    prompt = f"""You are a cautious trading assistant evaluating a stock trade.

Stock: {symbol}
Current Price: ${current_price}
RSI (14-day): {rsi:.1f}
Last 10 closing prices: {recent_prices}

The RSI has dropped below 30 (oversold signal).

Before approving, consider:
1. Does the price action look like normal overselling or a news-driven crash?
2. Is there a steady decline (concerning) or a sharp recent drop (possible panic sell)?
3. Does this look like a genuine rebound opportunity?

Respond with ONLY:
- First line: APPROVE or REJECT
- Second line: One sentence explaining why (max 20 words)

Be conservative — only APPROVE if the setup looks genuinely good."""

    message = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()
    print(f"  🤖 Claude says:\n     {response_text.replace(chr(10), chr(10) + '     ')}")
    return response_text.upper().startswith("APPROVE"), response_text