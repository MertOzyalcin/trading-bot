# 🛠️ Setup Guide

Complete step-by-step guide to get AlphaBot running on your machine.

---

## Prerequisites

- Python 3.10 or higher → [python.org](https://python.org)
- Git → [git-scm.com](https://git-scm.com)
- A free Alpaca account → [alpaca.markets](https://alpaca.markets)
- A free Anthropic account → [console.anthropic.com](https://console.anthropic.com)

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/MertOzyalcin/trading-bot.git
cd trading-bot
```

---

## Step 2 — Create a virtual environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt.

---

## Step 3 — Install dependencies

```bash
pip install alpaca-py pandas ta schedule python-dotenv anthropic flask yfinance backtesting certifi pandas-market-calendars beautifulsoup4 requests
```

This takes 1–2 minutes. All packages will install automatically.

---

## Step 4 — Get your API keys

### Alpaca (free paper trading account)
1. Go to [app.alpaca.markets](https://app.alpaca.markets)
2. Sign up for a free account
3. Go to **Paper Trading** → **API Keys**
4. Click **Generate New Key**
5. Copy your **API Key** and **Secret Key**

### Anthropic Claude (AI analysis)
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up for an account
3. Go to **API Keys** → **Create Key**
4. Copy your API key

---

## Step 5 — Create your `.env` file

Create a file called `.env` in the project root folder:

```
API_KEY=your_alpaca_api_key_here
SECRET_KEY=your_alpaca_secret_key_here
ANTHROPIC_KEY=your_anthropic_api_key_here
```

> ⚠️ Never share this file or commit it to GitHub. It's already in `.gitignore`.

---

## Step 6 — Configure the bot

Open `config.py` and adjust settings to your preference:

```python
# Stocks to watch
WATCHLIST = ["AAPL", "TSLA", "MSFT", "NVDA"]

# Schedule time — set to YOUR local time when US market opens
# US market opens 9:30 AM ET
# Istanbul (UTC+3): 16:31 summer / 17:31 winter
RUN_TIME = "16:31"

# Paper or live trading
PAPER_TRADING = True   # Always start with True
```

---

## Step 7 — Run the bot

```bash
python bot.py
```

You should see:
```
🟢 Bot started!
   Watching:    AAPL, TSLA, MSFT, NVDA
   ...
✅ Global checks passed
📊 AAPL
  Daily RSI: 44.2
  ...
```

---

## Step 8 — Open the dashboard

While the bot is running, open a **second terminal** and run:

```bash
python dashboard.py
```

Then open your browser and go to:
```
http://localhost:5000
```

---

## Step 9 — Run a backtest (optional)

```bash
python backtest.py
```

---

## Troubleshooting

### SSL Error on Windows
```bash
pip install --upgrade certifi
```
If still failing, move your project to `C:\trading-bot\` (avoid non-ASCII characters like ü in the path).

### `ModuleNotFoundError`
```bash
pip install <module-name>
```

### Bot says "TRADING BLOCKED"
This is normal — the bot detected a holiday, FOMC day, or market event. It will run again next scheduled time.

### Dashboard shows no data
Make sure `dashboard.py` is running in a separate terminal while you have the dashboard open in your browser.

---

## Switching to Live Trading

> ⚠️ Only do this after paper trading for at least 3–6 months.

1. Open `config.py`
2. Change `PAPER_TRADING = True` to `PAPER_TRADING = False`
3. Replace your Alpaca paper trading keys in `.env` with live trading keys
4. Start with a small amount you can afford to lose completely

---

## Getting Help

If you run into issues, open a GitHub Issue with:
- Your error message
- Which step you're on
- Your Python version (`python --version`)