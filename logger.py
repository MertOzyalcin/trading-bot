# ══════════════════════════════════════════════════════════════════════════════
# logger.py — CSV logging
# Saves every bot decision to bot_log.csv so you can review history
# ══════════════════════════════════════════════════════════════════════════════

from datetime import datetime
from config import LOG_FILE
import csv


def setup_log():
    """Creates bot_log.csv with column headers if it doesn't exist yet."""
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", newline="") as f:
            csv.writer(f).writerow([
                "timestamp",    # when the scan ran
                "symbol",       # which stock
                "price",        # closing price at scan time
                "rsi",          # RSI value
                "signal",       # BUY / SELL / HOLD
                "holding",      # did we own it at scan time
                "claude",       # APPROVE / REJECT / N/A
                "action",       # what the bot actually did
                "qty",          # shares bought/sold (0 if no action)
                "stop_loss",    # stop-loss price placed
                "take_profit",  # take-profit price placed
                "skip_reason"   # why the trade was skipped (if applicable)
            ])
        print(f"📋 Log file created: {LOG_FILE}")
    else:
        print(f"📋 Logging to: {LOG_FILE}")


def write_log(symbol, price, rsi, signal, holding, claude,
              action, qty=0, stop=0, profit=0, skip_reason=""):
    """Appends one row to bot_log.csv for every stock scanned."""
    with open(LOG_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol,
            round(price, 2),
            round(rsi, 1),
            signal,
            holding,
            claude,
            action,
            qty,
            stop,
            profit,
            skip_reason
        ])