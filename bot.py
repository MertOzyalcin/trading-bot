# ══════════════════════════════════════════════════════════════════════════════
# bot.py — Main entry point
# This file just runs the bot. All logic lives in separate modules.
#
# Project structure:
#   bot.py        ← you are here (runs the bot)
#   config.py     ← all settings (watchlist, risk %, schedule time, etc.)
#   strategy.py   ← RSI signal + Claude AI analysis
#   orders.py     ← placing and closing orders
#   safety.py     ← all safety checks
#   logger.py     ← CSV logging
#   skip_days.py  ← auto-detects holidays, FOMC, CPI days
# ══════════════════════════════════════════════════════════════════════════════

from datetime import datetime
from config   import WATCHLIST, RUN_TIME
from strategy import get_closes, get_signal, claude_approves
from orders   import get_qty, has_position, place_bracket_order, close_position
from safety   import run_global_safety_checks, run_stock_safety_checks
from logger   import setup_log, write_log
import schedule, time


# ══════════════════════════════════════════════════════════════════════════════
# MAIN BOT LOGIC
# ══════════════════════════════════════════════════════════════════════════════

def run_bot():
    print(f"\n🤖 [{datetime.now():%H:%M:%S}] Bot v6 — Running safety checks...")
    print(f"{'─' * 50}")

    # ── STEP 1: GLOBAL SAFETY CHECKS ──────────────────────────────────────────
    # Checks that apply to ALL stocks.
    # If any fail, the entire scan is blocked — no orders placed today.
    safe, reason = run_global_safety_checks()
    if not safe:
        print(f"\n🛑 TRADING BLOCKED — {reason}")
        print(f"   No orders will be placed. Trying again next scheduled run.")
        print(f"{'─' * 50}")
        return

    print(f"✅ All global checks passed — scanning {len(WATCHLIST)} stocks...")
    print(f"{'─' * 50}")

    # ── STEP 2: SCAN EACH STOCK ───────────────────────────────────────────────
    for symbol in WATCHLIST:
        print(f"\n📊 {symbol}")
        try:
            # Fetch price data and calculate RSI signal
            closes          = get_closes(symbol)
            signal, rsi_val = get_signal(closes)
            price           = float(closes.iloc[-1])
            holding         = has_position(symbol)

            print(f"  Price:   ${price:.2f}")
            print(f"  Signal:  {signal}")
            print(f"  Holding: {holding}")

            # ── BUY LOGIC ─────────────────────────────────────────────────────
            if signal == "BUY" and not holding:

                # Step 2a: Stock-level safety checks
                # (single-day crash check + earnings check)
                stock_safe, skip_reason = run_stock_safety_checks(symbol, closes)
                if not stock_safe:
                    print(f"  🛑 SKIPPED — {skip_reason}")
                    write_log(symbol, price, rsi_val, signal, holding,
                              "N/A", "SKIPPED", skip_reason=skip_reason)
                    continue

                # Step 2b: Claude AI second opinion
                print(f"  🔍 Asking Claude for analysis...")
                approved, claude_response = claude_approves(symbol, rsi_val, closes)

                if approved:
                    # All checks passed — place the trade
                    qty = get_qty(price)
                    stop, profit = place_bracket_order(symbol, qty, price)
                    write_log(symbol, price, rsi_val, signal, holding,
                              "APPROVE", "BUY", qty, stop, profit)
                else:
                    print(f"  ⛔ Claude rejected — skipping.")
                    write_log(symbol, price, rsi_val, signal, holding,
                              "REJECT", "REJECTED_BY_AI")

            # ── SELL LOGIC ────────────────────────────────────────────────────
            elif signal == "SELL" and holding:
                # Safety checks don't block sells
                # Always exit a position when the signal says overbought
                close_position(symbol)
                write_log(symbol, price, rsi_val, signal, holding,
                          "N/A", "SELL")

            # ── HOLD ──────────────────────────────────────────────────────────
            else:
                write_log(symbol, price, rsi_val, signal, holding,
                          "N/A", "HOLD")
                print(f"  ⏳ No action.")

        except Exception as e:
            print(f"  ❌ Error on {symbol}: {e}")

    print(f"\n{'─' * 50}")
    print("✅ Scan complete. Waiting for next run...")


# ══════════════════════════════════════════════════════════════════════════════
# SCHEDULE — runs Monday–Friday at RUN_TIME (set in config.py)
# ══════════════════════════════════════════════════════════════════════════════

schedule.every().monday.at(RUN_TIME).do(run_bot)
schedule.every().tuesday.at(RUN_TIME).do(run_bot)
schedule.every().wednesday.at(RUN_TIME).do(run_bot)
schedule.every().thursday.at(RUN_TIME).do(run_bot)
schedule.every().friday.at(RUN_TIME).do(run_bot)


# ══════════════════════════════════════════════════════════════════════════════
# START
# ══════════════════════════════════════════════════════════════════════════════

print("🟢 Bot v6 started!")
print(f"   Watching:      {', '.join(WATCHLIST)}")
print(f"   Risk/trade:    2% | Stop: -5% | Target: +10%")
print(f"   AI analysis:   ✅ Claude-powered")
print(f"   Safety checks: ✅ Holidays / FOMC / CPI / Crash / Earnings / Hours")
print(f"   Scheduled:     {RUN_TIME} Istanbul time")
print(f"   (Press Ctrl+C to stop)\n")

setup_log()
run_bot()   # run once immediately to test

# ── KEEP ALIVE ─────────────────────────────────────────────────────────────────
while True:
    schedule.run_pending()
    now = datetime.now()
    if now.minute % 5 == 0 and now.second < 60:
        print(f"💓 [{now:%H:%M}] Bot alive — next run at {RUN_TIME}")
    time.sleep(60)