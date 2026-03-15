<<<<<<< HEAD
# ── IMPORTS ────────────────────────────────────────────────────────────────────
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
=======
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
>>>>>>> b48f3b22f621f12ceb73e670a9d58b7cc4ced71a
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
<<<<<<< HEAD
import anthropic
import ta, schedule, time, os


# ── CONFIG ─────────────────────────────────────────────────────────────────────
load_dotenv()
API_KEY        = os.getenv("API_KEY")
SECRET         = os.getenv("SECRET_KEY")
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_KEY")

WATCHLIST   = ["AAPL", "TSLA", "MSFT", "NVDA"]
RISK_PCT    = 0.02
STOP_PCT    = 0.05
PROFIT_PCT  = 0.10


# ── CONNECT ────────────────────────────────────────────────────────────────────
trader        = TradingClient(API_KEY, SECRET, paper=True)
data          = StockHistoricalDataClient(API_KEY, SECRET)
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)


# ── FETCH PRICES ───────────────────────────────────────────────────────────────
def get_closes(symbol):
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=60)
    )
    bars = data.get_stock_bars(req).df
    return bars["close"]


# ── RSI SIGNAL ─────────────────────────────────────────────────────────────────
def get_signal(closes):
    rsi = ta.momentum.RSIIndicator(closes, 14).rsi().iloc[-1]
    print(f"  RSI: {rsi:.1f}")

    if rsi < 30:   return "BUY",  rsi
    elif rsi > 70: return "SELL", rsi
    else:          return "HOLD", rsi


# ── CLAUDE AI ANALYSIS ─────────────────────────────────────────────────────────
def claude_approves(symbol, rsi, closes):
    recent_prices = [round(float(p), 2) for p in closes.tail(10).tolist()]
    current_price = recent_prices[-1]

    prompt = f"""You are a cautious trading assistant helping evaluate a stock trade.

Stock: {symbol}
Current Price: ${current_price}
RSI (14-day): {rsi:.1f}
Last 10 closing prices: {recent_prices}

The RSI has dropped below 30, suggesting the stock may be oversold and due for a rebound.

Analyze this situation briefly and respond with ONLY:
- First line: APPROVE or REJECT
- Second line: One sentence explaining why (max 20 words)

Be conservative — only APPROVE if the setup looks genuinely good."""

    message = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text.strip()
    print(f"  🤖 Claude says:\n     {response_text.replace(chr(10), chr(10) + '     ')}")

    return response_text.upper().startswith("APPROVE")


# ── POSITION SIZING ────────────────────────────────────────────────────────────
def get_qty(price):
    balance = float(trader.get_account().cash)
    qty = int((balance * RISK_PCT) / (price * STOP_PCT))
    return max(1, qty)


# ── POSITION CHECK ─────────────────────────────────────────────────────────────
def has_position(symbol):
    try:
        pos = trader.get_open_position(symbol)
        return float(pos.qty) > 0
    except:
        return False


# ── PLACE BRACKET ORDER ────────────────────────────────────────────────────────
def place_bracket_order(symbol, qty, price):
    stop_price   = round(price * (1 - STOP_PCT), 2)
    profit_price = round(price * (1 + PROFIT_PCT), 2)

    print(f"  Stop-loss:   ${stop_price}")
    print(f"  Take-profit: ${profit_price}")

    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
        order_class=OrderClass.BRACKET,
        stop_loss=StopLossRequest(stop_price=stop_price),
        take_profit=TakeProfitRequest(limit_price=profit_price)
    )
    trader.submit_order(order)
    print(f"  ✅ BUY {qty} share(s) of {symbol} with bracket protection")


# ── CLOSE POSITION ─────────────────────────────────────────────────────────────
def close_position(symbol):
    trader.close_position(symbol)
    print(f"  ✅ Closed full position in {symbol}")


# ── MAIN BOT LOGIC ─────────────────────────────────────────────────────────────
def run_bot():
    print(f"\n🤖 [{datetime.now():%H:%M:%S}] Scanning {len(WATCHLIST)} stocks...")
    print(f"{'─' * 45}")

    for symbol in WATCHLIST:
        print(f"\n📊 {symbol}")
        try:
            closes          = get_closes(symbol)
            signal, rsi_val = get_signal(closes)
            price           = float(closes.iloc[-1])
            holding         = has_position(symbol)

            print(f"  Price:   ${price:.2f}")
            print(f"  Signal:  {signal}")
            print(f"  Holding: {holding}")

            if signal == "BUY" and not holding:
                print(f"  🔍 Asking Claude for analysis...")
                approved = claude_approves(symbol, rsi_val, closes)

                if approved:
                    qty = get_qty(price)
                    place_bracket_order(symbol, qty, price)
                else:
                    print(f"  ⛔ Claude rejected the trade — skipping.")

            elif signal == "SELL" and holding:
                close_position(symbol)

            else:
                print(f"  ⏳ No action.")

        except Exception as e:
            print(f"  ❌ Error on {symbol}: {e}")

    print(f"\n{'─' * 45}")
    print("✅ Scan complete. Waiting for next run...")


# ── SCHEDULE ───────────────────────────────────────────────────────────────────
# EDT (Mar–Nov): 16:31 Istanbul | EST (Nov–Mar): change to 17:31
RUN_TIME = "16:31"

schedule.every().monday.at(RUN_TIME).do(run_bot)
schedule.every().tuesday.at(RUN_TIME).do(run_bot)
schedule.every().wednesday.at(RUN_TIME).do(run_bot)
schedule.every().thursday.at(RUN_TIME).do(run_bot)
schedule.every().friday.at(RUN_TIME).do(run_bot)


# ── START ──────────────────────────────────────────────────────────────────────
print("🟢 Bot v4 started!")
print(f"   Watching:       {', '.join(WATCHLIST)}")
print(f"   Risk per trade: {RISK_PCT * 100}%")
print(f"   Stop-loss:      -{STOP_PCT * 100}%")
print(f"   Take-profit:    +{PROFIT_PCT * 100}%")
print(f"   AI analysis:    ✅ Claude-powered")
print(f"   Scheduled:      {RUN_TIME} Istanbul time (EDT season)")
print(f"   (Press Ctrl+C to stop)\n")

run_bot()

# ── LOOP ───────────────────────────────────────────────────────────────────────
while True:
    schedule.run_pending()
    now = datetime.now()
    if now.minute % 5 == 0 and now.second < 60:
        print(f"💓 [{now:%H:%M}] Bot alive — next run at {RUN_TIME}")
    time.sleep(60)
=======
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
>>>>>>> b48f3b22f621f12ceb73e670a9d58b7cc4ced71a
