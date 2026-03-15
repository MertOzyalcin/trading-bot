from flask import Flask, render_template, jsonify, request
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import anthropic
import yfinance as yf
import ta, os, csv, pathlib, json
import pandas as pd
import numpy as np

load_dotenv()

API_KEY       = os.getenv("API_KEY")
SECRET        = os.getenv("SECRET_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_KEY")
LOG_FILE      = pathlib.Path(__file__).parent / "bot_log.csv"

WATCHLIST  = ["AAPL", "TSLA", "MSFT", "NVDA"]
STOP_PCT   = 0.05
PROFIT_PCT = 0.10

trader        = TradingClient(API_KEY, SECRET, paper=True)
data_client   = StockHistoricalDataClient(API_KEY, SECRET)
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

app = Flask(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# BUILT-IN STRATEGIES
# ══════════════════════════════════════════════════════════════════════════════

class RSIStrategy(Strategy):
    """Buy when RSI < 30 (oversold), sell when RSI > 70 (overbought)."""
    rsi_low  = 30
    rsi_high = 70

    def init(self):
        close = pd.Series(self.data.Close)
        self.rsi = self.I(
            lambda x: ta.momentum.RSIIndicator(pd.Series(x), 14).rsi().values,
            close
        )

    def next(self):
        if self.rsi[-1] < self.rsi_low and not self.position.is_long:
            self.buy(size=0.95)
        elif self.rsi[-1] > self.rsi_high and self.position.is_long:
            self.sell()


class MACDStrategy(Strategy):
    """Buy when MACD crosses above signal line, sell when it crosses below."""

    def init(self):
        close        = pd.Series(self.data.Close)
        macd_obj     = ta.trend.MACD(close)
        self.macd    = self.I(lambda: macd_obj.macd().values)
        self.signal  = self.I(lambda: macd_obj.macd_signal().values)

    def next(self):
        if crossover(self.macd, self.signal) and not self.position.is_long:
            self.buy(size=0.95)
        elif crossover(self.signal, self.macd) and self.position.is_long:
            self.sell()


class MAStrategy(Strategy):
    """Buy when 50-day MA crosses above 200-day MA (golden cross)."""
    fast = 50
    slow = 200

    def init(self):
        c = self.data.Close
        self.fast_ma = self.I(lambda x: pd.Series(x).rolling(self.fast).mean().values, c)
        self.slow_ma = self.I(lambda x: pd.Series(x).rolling(self.slow).mean().values, c)

    def next(self):
        if crossover(self.fast_ma, self.slow_ma) and not self.position.is_long:
            self.buy(size=0.95)
        elif crossover(self.slow_ma, self.fast_ma) and self.position.is_long:
            self.sell()


class BollingerStrategy(Strategy):
    """Buy when price touches lower Bollinger Band, sell at upper band."""

    def init(self):
        close      = pd.Series(self.data.Close)
        bb         = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        self.upper = self.I(lambda: bb.bollinger_hband().values)
        self.lower = self.I(lambda: bb.bollinger_lband().values)

    def next(self):
        if self.data.Close[-1] < self.lower[-1] and not self.position.is_long:
            self.buy(size=0.95)
        elif self.data.Close[-1] > self.upper[-1] and self.position.is_long:
            self.sell()


STRATEGY_MAP = {
    "rsi":       RSIStrategy,
    "macd":      MACDStrategy,
    "ma_cross":  MAStrategy,
    "bollinger": BollingerStrategy,
}


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_rsi_data():
    results = []
    for symbol in WATCHLIST:
        try:
            req    = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=60)
            )
            bars   = data_client.get_stock_bars(req).df
            closes = bars["close"]
            rsi    = ta.momentum.RSIIndicator(closes, 14).rsi().iloc[-1]
            price  = float(closes.iloc[-1])
            signal = "BUY" if rsi < 30 else ("SELL" if rsi > 70 else "HOLD")
            results.append({"symbol": symbol, "price": round(price, 2),
                            "rsi": round(float(rsi), 1), "signal": signal})
        except Exception as e:
            results.append({"symbol": symbol, "price": 0, "rsi": 0,
                            "signal": "ERROR", "error": str(e)})
    return results


def get_positions():
    results = []
    try:
        for pos in trader.get_all_positions():
            entry = float(pos.avg_entry_price)
            results.append({
                "symbol":      pos.symbol,
                "qty":         int(float(pos.qty)),
                "entry":       round(entry, 2),
                "price":       round(float(pos.current_price), 2),
                "pl":          round(float(pos.unrealized_pl), 2),
                "pl_pct":      round(float(pos.unrealized_plpc) * 100, 2),
                "stop_loss":   round(entry * (1 - STOP_PCT), 2),
                "take_profit": round(entry * (1 + PROFIT_PCT), 2),
            })
    except:
        pass
    return results


def get_account():
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
    rows = []
    if not LOG_FILE.exists():
        return rows
    try:
        with open(LOG_FILE, "r") as f:
            for row in csv.DictReader(f):
                rows.append(row)
        return list(reversed(rows))[:50]
    except:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def run_backtest_engine(symbol, period, strategy_cls):
    df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

    if df.empty:
        raise ValueError(f"No data returned for {symbol}")

    bt      = Backtest(df, strategy_cls, cash=10000,
                       commission=0.002, finalize_trades=True)
    results = bt.run()

    # Equity curve
    eq          = results._equity_curve["Equity"]
    equity_data = [{"date": str(d.date()), "value": round(float(v), 2)}
                   for d, v in eq.items()]

    # Trades
    trade_list = []
    if not results._trades.empty:
        for _, t in results._trades.iterrows():
            trade_list.append({
                "entry":  str(t["EntryTime"].date()),
                "exit":   str(t["ExitTime"].date()),
                "pnl":    round(float(t["PnL"]), 2),
                "return": round(float(t["ReturnPct"]) * 100, 2),
            })

    def safe(key, default=0):
        v = results.get(key, default)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return default
        return round(float(v), 2)

    stats = {
        "return":      safe("Return [%]"),
        "buyhold":     safe("Buy & Hold Return [%]"),
        "trades":      int(results.get("# Trades", 0)),
        "winrate":     safe("Win Rate [%]"),
        "maxdrawdown": safe("Max. Drawdown [%]"),
        "sharpe":      safe("Sharpe Ratio"),
    }

    return {"stats": stats, "equity": equity_data, "trades": trade_list}


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    return jsonify({
        "rsi":       get_rsi_data(),
        "positions": get_positions(),
        "account":   get_account(),
        "log":       get_log(),
        "updated":   datetime.now().strftime("%H:%M:%S")
    })


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — BACKTEST LAB
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/backtest")
def backtest_page():
    return render_template("backtest.html")


@app.route("/learn")
def learn_page():
    return render_template("learn.html")


@app.route("/api/run-backtest", methods=["POST"])
def api_run_backtest():
    body     = request.get_json()
    symbol   = body.get("symbol", "AAPL").upper().strip()
    period   = body.get("period", "1y")
    strategy = body.get("strategy", "rsi")
    code     = body.get("code", "").strip()

    try:
        if strategy in ("custom", "ai") and code:
            local_ns = {
                "Strategy": Strategy, "crossover": crossover,
                "pd": pd, "ta": ta, "np": np,
            }
            exec(code, local_ns)
            strategy_cls = local_ns.get("CustomStrategy")
            if strategy_cls is None:
                return jsonify({"error": "Code must define a class named CustomStrategy"}), 400
        elif strategy in STRATEGY_MAP:
            strategy_cls = STRATEGY_MAP[strategy]
        else:
            return jsonify({"error": f"Unknown strategy: {strategy}"}), 400

        result = run_backtest_engine(symbol, period, strategy_cls)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate-strategy", methods=["POST"])
def api_generate_strategy():
    body   = request.get_json()
    prompt = body.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    system = """You are an expert algorithmic trading developer.
Generate a Python strategy class compatible with the backtesting.py library.

Rules:
- The class MUST be named exactly: CustomStrategy
- It MUST extend Strategy
- It MUST implement init(self) and next(self)
- Use self.I() to register all indicators
- Available imports already in scope: Strategy, crossover, pd, ta, np
- Use ta library for indicators (ta.momentum, ta.trend, ta.volatility)
- Buy with: self.buy(size=0.95)
- Sell with: self.sell()
- Check position with: self.position.is_long
- Return ONLY raw Python class code. No explanation, no markdown, no backticks."""

    try:
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        code = message.content[0].text.strip()
        code = code.replace("```python", "").replace("```", "").strip()
        return jsonify({"code": code})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🌐 Dashboard  → http://localhost:5000")
    print("🔬 Backtest   → http://localhost:5000/backtest")
    print("   Press Ctrl+C to stop\n")
    app.run(debug=False, port=5000)