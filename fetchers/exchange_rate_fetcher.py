import requests
from datetime import datetime, timedelta
import pytz

BUDAPEST_TZ = pytz.timezone("Europe/Budapest")

def _get_prev_business_day_from(date_str: str) -> str:
    """
    Given a date string (YYYY-MM-DD), return the closest prior business day
    (Mon-Fri) in the same format.  Used to find the trading day *before*
    whatever date Frankfurter's /latest endpoint actually represents.
    """
    anchor = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=BUDAPEST_TZ)
    day = anchor - timedelta(days=1)
    while day.weekday() >= 5:   # 5 = Saturday, 6 = Sunday
        day -= timedelta(days=1)
    return day.strftime("%Y-%m-%d")


def get_exchange_rates():
    """
    Fetch the latest EUR→HUF and USD→HUF exchange rates using the free Frankfurter API.
    Also fetches the previous business day's rates and calculates the daily % change
    to enable smart volatility-based commentary in the script generator.

    Returns a dict with:
      - eur_huf, usd_huf: today's rates
      - eur_huf_prev, usd_huf_prev: previous business day's rates (may be None)
      - eur_change_pct, usd_change_pct: % change vs. prev day (positive = HUF weakened)
      - high_volatility: True if either pair moved >= 1% vs. previous day
      - summary: concise one-line summary for the script
    """
    today_url = "https://api.frankfurter.app/latest?from=EUR&to=HUF,USD"

    result = {
        "eur_huf":        None,
        "usd_huf":        None,
        "eur_huf_prev":   None,
        "usd_huf_prev":   None,
        "eur_change_pct": None,
        "usd_change_pct": None,
        "high_volatility": False,
        "summary": "Exchange rate data is currently unavailable."
    }

    # ── Fetch today (latest settled rate) ────────────────────────────────────
    latest_date = None   # will be set from API response
    try:
        print("💱 Fetching today's exchange rates from Frankfurter API...")
        resp = requests.get(today_url, timeout=10)
        resp.raise_for_status()
        data  = resp.json()
        rates = data.get("rates", {})
        latest_date = data.get("date")   # e.g. "2026-05-06"

        eur_huf = rates.get("HUF")
        eur_usd = rates.get("USD")

        if eur_huf and eur_usd:
            result["eur_huf"] = eur_huf
            result["usd_huf"] = round(eur_huf / eur_usd, 2)
            print(f"  ✔️  Latest ({latest_date}): 1 EUR = {result['eur_huf']} HUF | 1 USD = {result['usd_huf']} HUF")

    except Exception as e:
        print(f"  ⚠️  Could not fetch today's exchange rates: {e}")

    # ── Determine previous business day relative to the date /latest returned ─
    # This is critical: /latest already returns a past date (the most recent
    # settled trading day).  Using system-clock "yesterday" risks landing on
    # the same date, making the change rate always 0%.
    if latest_date:
        prev_day_str = _get_prev_business_day_from(latest_date)
    else:
        # Fallback: go back 2 calendar days from today (covers weekend edge case)
        from datetime import date as _date
        fallback = datetime.now(BUDAPEST_TZ) - timedelta(days=2)
        while fallback.weekday() >= 5:
            fallback -= timedelta(days=1)
        prev_day_str = fallback.strftime("%Y-%m-%d")

    prev_url = f"https://api.frankfurter.app/{prev_day_str}?from=EUR&to=HUF,USD"

    # ── Fetch previous business day ──────────────────────────────────────────
    try:
        print(f"💱 Fetching previous business day's rates ({prev_day_str}) for volatility check...")
        resp_prev = requests.get(prev_url, timeout=10)
        resp_prev.raise_for_status()
        data_prev  = resp_prev.json()
        rates_prev = data_prev.get("rates", {})

        eur_huf_prev = rates_prev.get("HUF")
        eur_usd_prev = rates_prev.get("USD")

        if eur_huf_prev and eur_usd_prev:
            result["eur_huf_prev"] = eur_huf_prev
            result["usd_huf_prev"] = round(eur_huf_prev / eur_usd_prev, 2)
            print(f"  ✔️  Prev day: 1 EUR = {result['eur_huf_prev']} HUF | 1 USD = {result['usd_huf_prev']} HUF")

    except Exception as e:
        print(f"  ⚠️  Could not fetch previous day's exchange rates: {e}")

    # ── Calculate % change & determine volatility ────────────────────────────
    VOLATILITY_THRESHOLD = 1.0   # percent

    if result["eur_huf"] and result["eur_huf_prev"]:
        result["eur_change_pct"] = round(
            (result["eur_huf"] - result["eur_huf_prev"]) / result["eur_huf_prev"] * 100, 3
        )
    if result["usd_huf"] and result["usd_huf_prev"]:
        result["usd_change_pct"] = round(
            (result["usd_huf"] - result["usd_huf_prev"]) / result["usd_huf_prev"] * 100, 3
        )

    eur_vol = abs(result["eur_change_pct"]) if result["eur_change_pct"] is not None else 0
    usd_vol = abs(result["usd_change_pct"]) if result["usd_change_pct"] is not None else 0
    result["high_volatility"] = (eur_vol >= VOLATILITY_THRESHOLD or usd_vol >= VOLATILITY_THRESHOLD)

    # ── Build summary string ─────────────────────────────────────────────────
    if result["eur_huf"] and result["usd_huf"]:
        trend_eur = ""
        if result["eur_change_pct"] is not None:
            # Always show explicit sign for clarity: +0.5% or -0.8%
            sign = "+" if result["eur_change_pct"] >= 0 else ""
            trend_eur = f" ({sign}{result['eur_change_pct']}% vs prev day)"

        trend_usd = ""
        if result["usd_change_pct"] is not None:
            sign = "+" if result["usd_change_pct"] >= 0 else ""
            trend_usd = f" ({sign}{result['usd_change_pct']}% vs prev day)"

        result["summary"] = (
            f"1 EUR = {result['eur_huf']} HUF{trend_eur} | "
            f"1 USD = {result['usd_huf']} HUF{trend_usd}"
        )
        volatility_label = "⚠️  HIGH VOLATILITY" if result["high_volatility"] else "✅ Low volatility"
        print(f"  {volatility_label} — {result['summary']}")

    return result


if __name__ == "__main__":
    rates = get_exchange_rates()
    print("\nFull result:")
    for k, v in rates.items():
        print(f"  {k}: {v}")
