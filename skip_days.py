# skip_days.py
# ─────────────────────────────────────────────────────────────────────────────
# Automatically detects dates the bot should skip trading:
#   1. NYSE market holidays (exchange closed)
#   2. Fed FOMC announcement days
#   3. Major economic events (CPI, Jobs Report, etc.)
#
# Usage:
#   from skip_days import should_skip_today
#   safe, reason = should_skip_today()
# ─────────────────────────────────────────────────────────────────────────────

import pandas_market_calendars as mcal   # NYSE holiday calendar
import requests                           # HTTP requests for Fed + economic data
from bs4 import BeautifulSoup            # HTML parsing
from datetime import date, timedelta
import json, re, os, pathlib

# Cache file — stores fetched FOMC and economic dates for 7 days
# so we don't hammer external websites on every bot run
CACHE_FILE = pathlib.Path(__file__).parent / "skip_days_cache.json"
CACHE_DAYS = 7   # refresh cache every 7 days


# ══════════════════════════════════════════════════════════════════════════════
# CACHE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def load_cache():
    """Load cached skip dates from disk."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_cache(data):
    """Save skip dates to disk."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"  ⚠️ Could not save skip_days cache: {e}")


def cache_is_fresh(cache):
    """Returns True if cache was updated within the last CACHE_DAYS days."""
    if "last_updated" not in cache:
        return False
    last = date.fromisoformat(cache["last_updated"])
    return (date.today() - last).days < CACHE_DAYS


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 1 — NYSE MARKET HOLIDAYS
# ══════════════════════════════════════════════════════════════════════════════

def get_nyse_holidays(year=None):
    """
    Returns a set of date strings (YYYY-MM-DD) when NYSE is closed.
    Uses pandas_market_calendars — no internet required, data is built in.
    """
    if year is None:
        year = date.today().year

    nyse     = mcal.get_calendar("NYSE")
    # get_schedule returns only TRADING days — we want the inverse
    # So we check what days are missing from Jan 1 to Dec 31
    start    = f"{year}-01-01"
    end      = f"{year}-12-31"
    schedule = nyse.schedule(start_date=start, end_date=end)

    # All weekdays this year
    all_weekdays = set(
        str(d.date()) for d in
        mcal.date_range(
            mcal.get_calendar("NYSE").schedule(start_date=start, end_date=end),
            frequency="1D"
        )
    )

    # All calendar weekdays (Mon-Fri) this year
    import pandas as pd
    all_cal_weekdays = set(
        str(d.date()) for d in
        pd.date_range(start=start, end=end, freq="B")
    )

    # Holidays = weekdays where NYSE is closed
    holidays = all_cal_weekdays - all_weekdays
    return holidays


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 2 — FED FOMC ANNOUNCEMENT DAYS
# ══════════════════════════════════════════════════════════════════════════════

def fetch_fomc_dates():
    """
    Scrapes the Federal Reserve's official FOMC calendar page.
    Returns a list of date strings (YYYY-MM-DD) when rate decisions are announced.
    The Fed publishes the full year calendar at the start of each year.
    """
    dates = []
    try:
        url      = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
        headers  = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup     = BeautifulSoup(response.text, "html.parser")

        year = date.today().year

        # The Fed page lists meeting dates in a structured table
        # Each meeting shows start/end dates — we want the LAST day (announcement day)
        for panel in soup.find_all("div", class_=re.compile("panel")):
            text = panel.get_text()
            # Look for date patterns like "January 28-29" or "March 18-19"
            months = {
                "January":1,"February":2,"March":3,"April":4,
                "May":5,"June":6,"July":7,"August":8,
                "September":9,"October":10,"November":11,"December":12
            }
            for month_name, month_num in months.items():
                # Pattern: "Month D-D" or "Month D"
                patterns = [
                    rf"{month_name}\s+(\d+)[-–](\d+)",   # range like Jan 28-29
                    rf"{month_name}\s+(\d+)",              # single day
                ]
                for pattern in patterns:
                    match = re.search(pattern, text)
                    if match:
                        # Take the last day of the meeting (announcement day)
                        day = int(match.group(2) if len(match.groups()) > 1 else match.group(1))
                        try:
                            d = date(year, month_num, day)
                            dates.append(str(d))
                        except ValueError:
                            pass
                        break

        # Deduplicate and sort
        dates = sorted(set(dates))
        print(f"  📡 Fetched {len(dates)} FOMC dates from federalreserve.gov")

    except Exception as e:
        print(f"  ⚠️ Could not fetch FOMC dates: {e}")

    return dates


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 3 — MAJOR ECONOMIC EVENTS
# ══════════════════════════════════════════════════════════════════════════════

def fetch_economic_dates():
    """
    Fetches high-impact economic event dates from investing.com's economic calendar.
    Targets: CPI, Non-Farm Payrolls (Jobs Report), GDP, PPI, Retail Sales.
    These events cause sharp market moves that make RSI signals unreliable.
    """
    dates = []
    HIGH_IMPACT_KEYWORDS = [
        "Non-Farm",         # Jobs report — biggest monthly market mover
        "CPI",              # Consumer Price Index — inflation data
        "GDP",              # Gross Domestic Product
        "PPI",              # Producer Price Index
        "Retail Sales",     # Consumer spending data
        "FOMC",             # Fed minutes/statements (backup to direct scrape)
        "Fed Chair",        # Fed Chair speeches (major market impact)
    ]

    try:
        # investing.com economic calendar — one of the most reliable free sources
        url     = "https://www.investing.com/economic-calendar/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup     = BeautifulSoup(response.text, "html.parser")

        # Parse the calendar table rows
        for row in soup.find_all("tr", class_=re.compile("js-event-item")):
            # Check impact level — we only want high impact (3 bull icons)
            impact = row.find("td", class_=re.compile("sentiment"))
            if not impact:
                continue
            bull_icons = impact.find_all("i", class_=re.compile("grayFullBullishIcon|fullBullishIcon"))
            if len(bull_icons) < 3:
                continue   # skip low/medium impact events

            # Check event name
            event_name = row.find("td", class_=re.compile("event"))
            if not event_name:
                continue
            name_text = event_name.get_text(strip=True)
            if not any(kw.lower() in name_text.lower() for kw in HIGH_IMPACT_KEYWORDS):
                continue

            # Get the date
            date_cell = row.get("data-event-datetime") or row.get("id", "")
            if date_cell:
                # Format is usually YYYY/MM/DD or similar
                date_match = re.search(r"(\d{4})[/-](\d{2})[/-](\d{2})", date_cell)
                if date_match:
                    y, m, d = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
                    try:
                        dates.append(str(date(y, m, d)))
                    except ValueError:
                        pass

        dates = sorted(set(dates))
        print(f"  📡 Fetched {len(dates)} high-impact economic dates")

    except Exception as e:
        print(f"  ⚠️ Could not fetch economic calendar: {e}")
        # Fallback: hardcode known recurring dates for current month
        # CPI is usually released on the 2nd Tuesday of each month
        # NFP is usually the first Friday of each month
        today    = date.today()
        year, month = today.year, today.month
        dates   += _get_fallback_dates(year, month)

    return dates


def _get_fallback_dates(year, month):
    """
    Fallback: estimate CPI and NFP dates using their typical release patterns.
    Used when web scraping fails.
      - NFP (Jobs): first Friday of the month
      - CPI:        second or third Tuesday of the month
    """
    import calendar
    fallback = []
    cal      = calendar.monthcalendar(year, month)

    # First Friday of the month
    for week in cal:
        if week[calendar.FRIDAY] != 0:
            fallback.append(str(date(year, month, week[calendar.FRIDAY])))
            break

    # Second Tuesday of the month
    tuesdays = [week[calendar.TUESDAY] for week in cal if week[calendar.TUESDAY] != 0]
    if len(tuesdays) >= 2:
        fallback.append(str(date(year, month, tuesdays[1])))

    return fallback


# ══════════════════════════════════════════════════════════════════════════════
# REFRESH CACHE
# ══════════════════════════════════════════════════════════════════════════════

def refresh_skip_days():
    """
    Fetches all skip day sources and saves to cache.
    Called automatically when cache is stale (older than 7 days).
    """
    print("\n🔄 Refreshing skip days cache...")

    fomc      = fetch_fomc_dates()
    economic  = fetch_economic_dates()
    holidays  = list(get_nyse_holidays())

    cache = {
        "last_updated": str(date.today()),
        "holidays":     sorted(holidays),
        "fomc":         sorted(fomc),
        "economic":     sorted(economic),
    }

    save_cache(cache)
    print(f"  ✅ Cache updated — {len(holidays)} holidays, {len(fomc)} FOMC, {len(economic)} economic events")
    return cache


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def should_skip_today():
    """
    Main function — call this from your bot.
    Returns (should_skip: bool, reason: str)

    Example:
        skip, reason = should_skip_today()
        if skip:
            print(f"Skipping today: {reason}")
    """
    today     = str(date.today())
    tomorrow  = str(date.today() + timedelta(days=1))

    # Load cache, refresh if stale
    cache = load_cache()
    if not cache_is_fresh(cache):
        cache = refresh_skip_days()

    holidays  = set(cache.get("holidays", []))
    fomc      = set(cache.get("fomc", []))
    economic  = set(cache.get("economic", []))

    # Check 1: NYSE closed today
    if today in holidays:
        return True, f"🏦 NYSE holiday — market is closed today ({today})"

    # Check 2: Fed FOMC announcement today
    if today in fomc:
        return True, f"🏛️ Fed FOMC rate decision today — market highly unpredictable"

    # Check 3: Major economic event today
    if today in economic:
        return True, f"📊 Major economic event today (CPI/Jobs/GDP) — signals unreliable"

    # Check 4: FOMC tomorrow — markets often move the day before too
    if tomorrow in fomc:
        return True, f"🏛️ Fed FOMC decision tomorrow — pre-announcement volatility expected"

    return False, ""


def print_upcoming_skip_days(days_ahead=30):
    """
    Utility: Print all skip days in the next N days.
    Call this manually to preview what days the bot will skip.
    """
    cache = load_cache()
    if not cache_is_fresh(cache):
        cache = refresh_skip_days()

    all_skip = (
        [(d, "NYSE Holiday") for d in cache.get("holidays", [])] +
        [(d, "Fed FOMC")     for d in cache.get("fomc", [])] +
        [(d, "Economic Event") for d in cache.get("economic", [])]
    )

    today  = date.today()
    cutoff = today + timedelta(days=days_ahead)

    upcoming = [
        (d, reason) for d, reason in all_skip
        if today <= date.fromisoformat(d) <= cutoff
    ]
    upcoming.sort(key=lambda x: x[0])

    print(f"\n📅 Upcoming skip days (next {days_ahead} days):")
    print(f"{'─' * 40}")
    if not upcoming:
        print("  None found")
    for d, reason in upcoming:
        print(f"  {d}  →  {reason}")
    print(f"{'─' * 40}\n")


# Run standalone to preview skip days
if __name__ == "__main__":
    print_upcoming_skip_days(60)