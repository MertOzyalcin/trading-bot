from flask import Flask, render_template, jsonify
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
import ta, os, csv, pathlib

load_dotenv()

API_KEY  = os.getenv("API_KEY")
SECRET   = os.getenv("SECRET_KEY")
LOG_FILE = pathlib.Path(__file__).parent / "bot_log.csv"

WATCHLIST  = ["AAPL", "TSLA", "MSFT", "NVDA"]
STOP_PCT   = 0.05
PROFIT_PCT = 0.10

trader = TradingClient(API_KEY, SECRET, paper=True)
data   = StockHistoricalDataClient(API_KEY, SECRET)

app = Flask(__name__)


# ── HELPERS ────────────────────────────────────────────────────────────────────

def get_rsi_data():
    """Fetch RSI for all watchlist stocks."""
    results = []
    for symbol in WATCHLIST:
        try:
            req  = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=60)
            )
            bars   = data.get_stock_bars(req).df
            closes = bars["close"]
            rsi    = ta.momentum.RSIIndicator(closes, 14).rsi().iloc[-1]
            price  = float(closes.iloc[-1])

            if rsi < 30:
                signal = "BUY"
            elif rsi > 70:
                signal = "SELL"
            else:
                signal = "HOLD"

            results.append({
                "symbol": symbol,
                "price":  round(price, 2),
                "rsi":    round(float(rsi), 1),
                "signal": signal
            })
        except Exception as e:
            results.append({
                "symbol": symbol,
                "price":  0,
                "rsi":    0,
                "signal": "ERROR",
                "error":  str(e)
            })
    return results


def get_positions():
    """Fetch open positions with P&L from Alpaca."""
    results = []
    try:
        positions = trader.get_all_positions()
        for pos in positions:
            entry  = float(pos.avg_entry_price)
            price  = float(pos.current_price)
            qty    = float(pos.qty)
            pl     = float(pos.unrealized_pl)
            pl_pct = float(pos.unrealized_plpc) * 100

            results.append({
                "symbol":      pos.symbol,
                "qty":         int(qty),
                "entry":       round(entry, 2),
                "price":       round(price, 2),
                "pl":          round(pl, 2),
                "pl_pct":      round(pl_pct, 2),
                "stop_loss":   round(entry * (1 - STOP_PCT), 2),
                "take_profit": round(entry * (1 + PROFIT_PCT), 2),
            })
    except Exception as e:
        pass
    return results


def get_account():
    """Fetch account balance info."""
    try:
        acct = trader.get_account()
        return {
            "cash":     round(float(acct.cash), 2),
            "equity":   round(float(acct.equity), 2),
            "pl_today": round(float(acct.equity) - float(acct.last_equity), 2)
        }
    except:
        return {"cash": 0, "equity": 0, "pl_today": 0}


def get_log():
    """Read bot_log.csv and return last 50 rows newest-first."""
    rows = []
    if not LOG_FILE.exists():
        return rows
    try:
        with open(LOG_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return list(reversed(rows))[:50]
    except:
        return []


# ── ROUTES ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    """Single endpoint — dashboard fetches everything from here."""
    return jsonify({
        "rsi":       get_rsi_data(),
        "positions": get_positions(),
        "account":   get_account(),
        "log":       get_log(),
        "updated":   datetime.now().strftime("%H:%M:%S")
    })


# ── RUN ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🌐 Dashboard running at http://localhost:5000")
    print("   Press Ctrl+C to stop\n")
    app.run(debug=False, port=5000)