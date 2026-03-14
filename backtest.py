# ── IMPORTS ────────────────────────────────────────────────────────────────────
# Run first: pip install yfinance backtesting
import ssl
import certifi
ssl._create_default_https_context = ssl.create_default_context(cafile=certifi.where())
import yfinance as yf                      # downloads free historical price data
from backtesting import Backtest, Strategy # backtesting framework
import ta
import pandas as pd


# ── STRATEGY ───────────────────────────────────────────────────────────────────
class RSIStrategy(Strategy):
    # These are the same thresholds your live bot uses
    # Try changing them and re-running to see if results improve
    rsi_low  = 30   # buy when RSI drops below this → oversold
    rsi_high = 70   # sell when RSI rises above this → overbought

    def init(self):
        # self.I() registers an indicator with the backtesting engine
        # We wrap the RSI calculation so the engine can track it across time
        close = pd.Series(self.data.Close)
        self.rsi = self.I(
            lambda x: ta.momentum.RSIIndicator(pd.Series(x), 14).rsi().values,
            close
        )

    def next(self):
        # This function runs once per day in the historical data
        # It simulates exactly what your live bot does each morning

        if self.rsi[-1] < self.rsi_low and not self.position.is_long:
            # RSI oversold + we don't hold → buy
            # size=0.95 means use 95% of available cash (5% buffer for fees)
            self.buy(size=0.95)

        elif self.rsi[-1] > self.rsi_high and self.position.is_long:
            # RSI overbought + we hold → sell everything
            self.sell()


# ── RUN BACKTEST FOR ONE SYMBOL ────────────────────────────────────────────────
def run_backtest(symbol, period="1y"):
    print(f"\n📊 Backtesting {symbol} over {period}...")

    # Download historical data from Yahoo Finance — completely free
    # auto_adjust=True adjusts prices for stock splits and dividends
    df = yf.download(symbol, period=period, auto_adjust=True, progress=False)

    # backtesting.py needs columns named exactly: Open, High, Low, Close, Volume
    # yfinance sometimes returns multi-level column names — this flattens them
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

    # Create and run the backtest
    # cash=10000     → start with $10,000 (matches a typical paper trading account)
    # commission=0.002 → 0.2% per trade (realistic brokerage fee simulation)
    bt      = Backtest(df, RSIStrategy, cash=10000, commission=0.002)
    results = bt.run()

    # Print the most useful metrics
    print(f"  {'─' * 40}")
    print(f"  Strategy Return: {results['Return [%]']:>8.1f}%")
    print(f"  Buy & Hold:      {results['Buy & Hold Return [%]']:>8.1f}%")
    print(f"  Total Trades:    {results['# Trades']:>8}")
    print(f"  Win Rate:        {results['Win Rate [%]']:>8.1f}%")
    print(f"  Max Drawdown:    {results['Max. Drawdown [%]']:>8.1f}%")
    print(f"  Sharpe Ratio:    {results['Sharpe Ratio']:>8.2f}")
    # Sharpe Ratio > 1.0 = good, > 2.0 = excellent
    # Max Drawdown = worst losing streak — lower is better
    # If Strategy Return < Buy & Hold, the strategy underperformed doing nothing

    return results


# ── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🔬 RSI Strategy Backtest")
    print("=" * 45)
    print("Testing your exact bot strategy on 1 year of real data...")

    # Test all 4 stocks from your watchlist
    symbols     = ["AAPL", "TSLA", "MSFT", "NVDA"]
    all_results = {}

    for symbol in symbols:
        all_results[symbol] = run_backtest(symbol, period="1y")

    # ── SUMMARY TABLE ──────────────────────────────────────────────────────────
    print(f"\n{'═' * 52}")
    print(f"  📈 SUMMARY — RSI(30/70) vs Buy & Hold")
    print(f"{'─' * 52}")
    print(f"  {'Symbol':<8} {'Strategy':>10} {'Buy&Hold':>10} {'Trades':>8} {'Win%':>8}")
    print(f"{'─' * 52}")

    for symbol, r in all_results.items():
        strategy = r['Return [%]']
        bh       = r['Buy & Hold Return [%]']
        trades   = r['# Trades']
        winrate  = r['Win Rate [%]']

        # Add a ✅ if strategy beat buy & hold, ❌ if it didn't
        beat = "✅" if strategy > bh else "❌"

        print(f"  {symbol:<8} {strategy:>9.1f}%  {bh:>9.1f}%  {trades:>7}  {winrate:>7.1f}%  {beat}")

    print(f"{'─' * 52}")
    print(f"\n  ✅ = strategy beat buy & hold")
    print(f"  ❌ = just holding was better\n")
    print("💡 Tips for reading results:")
    print("   • Win Rate above 50% means more winning trades than losing")
    print("   • Max Drawdown above -20% is a warning sign")
    print("   • Sharpe Ratio above 1.0 is considered good")
    print("   • If ❌ on most stocks, consider adjusting rsi_low/rsi_high")
    print("\n✅ Backtest complete.")