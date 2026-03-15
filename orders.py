# ══════════════════════════════════════════════════════════════════════════════
# orders.py — Order execution
# ══════════════════════════════════════════════════════════════════════════════

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest, StopLossRequest, TakeProfitRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from config import API_KEY, SECRET, RISK_PCT, STOP_PCT, PROFIT_PCT, PAPER_TRADING

# paper=True  → simulated money (safe)
# paper=False → real money (only after months of paper trading)
trader = TradingClient(API_KEY, SECRET, paper=PAPER_TRADING)

# Warn clearly if running in live mode
if not PAPER_TRADING:
    print("⚠️  LIVE TRADING MODE — Real money at risk!")
else:
    print("📄 Paper trading mode — No real money at risk")


def get_qty(price):
    """
    Calculates shares to buy using the 2% risk rule.
    If stock drops STOP_PCT (5%), loss = exactly RISK_PCT (2%) of account.
    Always buys at least 1 share.
    """
    balance = float(trader.get_account().cash)
    qty     = int((balance * RISK_PCT) / (price * STOP_PCT))
    return max(1, qty)


def has_position(symbol):
    """Returns True if we already own this stock."""
    try:
        pos = trader.get_open_position(symbol)
        return float(pos.qty) > 0
    except:
        return False


def place_bracket_order(symbol, qty, price):
    """
    Places a bracket order — 3 linked orders in one request:
      1. Market BUY  → executes immediately
      2. Stop-loss   → auto-sells if price drops STOP_PCT
      3. Take-profit → auto-sells if price rises PROFIT_PCT
    Alpaca manages orders 2 and 3 server-side — computer can be OFF.
    """
    stop_price   = round(price * (1 - STOP_PCT),  2)
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
    mode = "PAPER" if PAPER_TRADING else "LIVE"
    print(f"  ✅ [{mode}] BUY {qty} share(s) of {symbol}")
    return stop_price, profit_price


def close_position(symbol):
    """Sells entire position and cancels any open bracket orders."""
    trader.close_position(symbol)
    mode = "PAPER" if PAPER_TRADING else "LIVE"
    print(f"  ✅ [{mode}] Closed position in {symbol}")