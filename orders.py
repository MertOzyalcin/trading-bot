# ══════════════════════════════════════════════════════════════════════════════
# orders.py — Order execution
# Placing bracket orders and closing positions
# ══════════════════════════════════════════════════════════════════════════════

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest, StopLossRequest, TakeProfitRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from config import API_KEY, SECRET, RISK_PCT, STOP_PCT, PROFIT_PCT


# ── CLIENT ─────────────────────────────────────────────────────────────────────
trader = TradingClient(API_KEY, SECRET, paper=True)


def get_qty(price):
    """
    Calculates how many shares to buy using the 2% risk rule.

    Formula: qty = (cash × RISK_PCT) ÷ (price × STOP_PCT)

    Example with $10,000 account, AAPL at $250:
      qty = ($10,000 × 2%) ÷ ($250 × 5%)
      qty = $200 ÷ $12.50 = 16 shares
      If AAPL drops 5%: 16 × $12.50 = $200 loss = exactly 2% of account

    Always buys at least 1 share even if math rounds to 0.
    """
    balance = float(trader.get_account().cash)
    qty     = int((balance * RISK_PCT) / (price * STOP_PCT))
    return max(1, qty)


def has_position(symbol):
    """
    Returns True if we already own shares of this stock.
    Prevents the bot from buying the same stock twice.
    Alpaca raises an error if no position exists — we catch that and return False.
    """
    try:
        pos = trader.get_open_position(symbol)
        return float(pos.qty) > 0
    except:
        return False


def place_bracket_order(symbol, qty, price):
    """
    Places a bracket order — one request that creates 3 linked orders:

      1. Market BUY   → executes immediately at current price
      2. Stop-loss    → automatically sells if price drops STOP_PCT (5%)
      3. Take-profit  → automatically sells if price rises PROFIT_PCT (10%)

    Orders 2 and 3 are managed by Alpaca's servers.
    Your computer can be completely OFF and they will still trigger.

    Returns (stop_price, profit_price) for logging purposes.
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
    print(f"  ✅ BUY {qty} share(s) of {symbol} with bracket protection")
    return stop_price, profit_price


def close_position(symbol):
    """
    Sells our entire position in a stock.
    Also automatically cancels any open stop-loss/take-profit bracket orders.
    Used when RSI signals overbought on a stock we hold.
    """
    trader.close_position(symbol)
    print(f"  ✅ Closed full position in {symbol}")