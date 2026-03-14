from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
# ── CONFIG ────────────────────────────────
load_dotenv()
API_KEY    = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
SYMBOL     = "AAPL"
SHARES     = 1

# ── CONNECT ───────────────────────────────
trader  = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# ── STRATEGY ──────────────────────────────
def get_signal(symbol):
    # Fetch last 30 days of daily bars
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=30)
    )
    bars = data_client.get_stock_bars(request).df
    closes = bars["close"]

    # Moving averages
    short_ma = closes.tail(5).mean()   # 5-day
    long_ma  = closes.tail(20).mean()  # 20-day

    print(f"Short MA: {short_ma:.2f} | Long MA: {long_ma:.2f}")

    if short_ma > long_ma: return "BUY"
    if short_ma < long_ma: return "SELL"
    return "HOLD"

# ── EXECUTE ───────────────────────────────
def place_order(symbol, side):
    order = MarketOrderRequest(
        symbol=symbol,
        qty=SHARES,
        side=side,
        time_in_force=TimeInForce.DAY
    )
    trader.submit_order(order)
    print(f"✅ Order placed: {side} {SHARES} share(s) of {symbol}")

# ── MAIN ──────────────────────────────────
signal = get_signal(SYMBOL)
print(f"Signal for {SYMBOL}: {signal}")

if signal == "BUY":
    place_order(SYMBOL, OrderSide.BUY)
elif signal == "SELL":
    place_order(SYMBOL, OrderSide.SELL)
else:
    print("⏳ No action today.")