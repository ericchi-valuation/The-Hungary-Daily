import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz

BUDAPEST_TZ = pytz.timezone("Europe/Budapest")


def _get_prev_business_day_from(date_str: str) -> str:
    """
    Given a date string (YYYY-MM-DD), return the closest prior business day
    (Mon-Fri) in the same format.
    """
    anchor = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=BUDAPEST_TZ)
    day = anchor - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.strftime("%Y-%m-%d")


def _get_last_friday(reference: datetime) -> str:
    """Return the most recent Friday on or before the reference date."""
    day = reference
    while day.weekday() != 4:  # 4 = Friday
        day -= timedelta(days=1)
    return day.strftime("%Y-%m-%d")


def _get_friday_before(date_str: str) -> str:
    """Return the Friday before the given date (used for Monday's week-over-week)."""
    anchor = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=BUDAPEST_TZ)
    day = anchor - timedelta(days=1)
    while day.weekday() != 4:
        day -= timedelta(days=1)
    return day.strftime("%Y-%m-%d")


# =============================================================================
# Source A: Frankfurter API (primary)
# =============================================================================
def _fetch_frankfurter(date_param: str = "latest"):
    """
    Fetch from api.frankfurter.app.
    date_param: 'latest' or a YYYY-MM-DD string.
    Returns (eur_huf, eur_usd, date_str) or raises on failure.
    """
    if date_param == "latest":
        url = "https://api.frankfurter.app/latest?from=EUR&to=HUF,USD"
    else:
        url = f"https://api.frankfurter.app/{date_param}?from=EUR&to=HUF,USD"

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    rates = data.get("rates", {})
    return rates.get("HUF"), rates.get("USD"), data.get("date")


# =============================================================================
# Source B: European Central Bank (ECB) XML — free fallback, no API key
# Updates daily at ~16:00 CET with official reference rates
# =============================================================================
def _fetch_ecb():
    """
    Fetch EUR/HUF and EUR/USD from ECB's official daily XML feed.
    Returns (eur_huf, eur_usd, date_str) or raises on failure.
    """
    ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    resp = requests.get(ECB_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    # ECB XML namespace
    ns = {
        'gesmes': 'http://www.gesmes.org/xml/2002-08-01',
        'ecb':    'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'
    }

    # Find the date
    time_cube = root.find('.//ecb:Cube[@time]', ns)
    date_str = time_cube.attrib.get('time') if time_cube is not None else None

    # Collect all currency rates
    rates = {}
    for cube in root.findall('.//ecb:Cube[@currency]', ns):
        rates[cube.attrib['currency']] = float(cube.attrib['rate'])

    eur_huf = rates.get('HUF')
    eur_usd = rates.get('USD')

    if not eur_huf or not eur_usd:
        raise ValueError("ECB feed missing HUF or USD rate")

    return eur_huf, eur_usd, date_str


def _fetch_rates_with_fallback(date_param: str = "latest", label: str = "today"):
    """
    Try Frankfurter first; fall back to ECB if it fails.
    Returns (eur_huf, usd_huf, date_str, source_name) or (None, None, None, None).
    Note: ECB only supports 'latest', so historical date queries use Frankfurter only.
    """
    # ── Primary: Frankfurter ─────────────────────────────────────────────────
    try:
        eur_huf, eur_usd, date_str = _fetch_frankfurter(date_param)
        if eur_huf and eur_usd:
            usd_huf = round(eur_huf / eur_usd, 2)
            print(f"  ✔️  [{label}] Frankfurter: 1 EUR = {eur_huf} HUF | 1 USD = {usd_huf} HUF ({date_str})")
            return eur_huf, usd_huf, date_str, "Frankfurter"
    except Exception as e:
        print(f"  ⚠️  Frankfurter failed ({label}): {e}")

    # ── Fallback: ECB (only for latest rates, not historical) ─────────────────
    if date_param == "latest":
        try:
            print(f"  🔄  Trying ECB fallback for {label}...")
            eur_huf, eur_usd, date_str = _fetch_ecb()
            usd_huf = round(eur_huf / eur_usd, 2)
            print(f"  ✔️  [{label}] ECB: 1 EUR = {eur_huf} HUF | 1 USD = {usd_huf} HUF ({date_str})")
            return eur_huf, usd_huf, date_str, "ECB"
        except Exception as e2:
            print(f"  ⚠️  ECB also failed: {e2}")

    return None, None, None, None


# =============================================================================
# Main entry point
# =============================================================================
def get_exchange_rates():
    """
    Fetch EUR/HUF and USD/HUF with smart weekend/weekday logic:

    - Sunday:  Markets closed. Return a 'skip_segment' flag. The script
               generator will say nothing about rates (weekend, no new data).
    - Monday:  Show last Friday's close PLUS week-over-week change
               (last Friday vs. the Friday before that).
    - Tue–Sat: Standard: today's close vs. previous business day's close.

    Returns a dict with:
      eur_huf, usd_huf           — latest rates (may be None on failure)
      eur_huf_prev, usd_huf_prev — comparison rates
      eur_change_pct, usd_change — % change
      high_volatility            — True if either pair moved >= 1%
      rate_date                  — date of the latest rates
      prev_date                  — date of the comparison rates
      is_sunday                  — True if today is Sunday (no segment needed)
      is_monday                  — True if today is Monday (show weekly context)
      comparison_label           — human-readable label: "prev day" or "last week"
      summary                    — one-line text for the script generator
    """
    now_budapest = datetime.now(BUDAPEST_TZ)
    weekday = now_budapest.weekday()  # 0=Mon, 6=Sun

    result = {
        "eur_huf":          None,
        "usd_huf":          None,
        "eur_huf_prev":     None,
        "usd_huf_prev":     None,
        "eur_change_pct":   None,
        "usd_change_pct":   None,
        "high_volatility":  False,
        "rate_date":        None,
        "prev_date":        None,
        "is_sunday":        weekday == 6,
        "is_monday":        weekday == 0,
        "comparison_label": "prev day",
        "summary":          "Exchange rate data is currently unavailable.",
    }

    # ── Sunday: no market data, skip the segment entirely ─────────────────────
    if weekday == 6:
        result["summary"] = "SUNDAY_NO_RATES"
        print("💱 Sunday — markets closed. Skipping exchange rate segment.")
        return result

    # ── Fetch latest rates (Frankfurter → ECB fallback) ───────────────────────
    print("💱 Fetching today's exchange rates from Frankfurter API...")
    eur_huf, usd_huf, rate_date, _ = _fetch_rates_with_fallback("latest", "latest")
    result["eur_huf"]   = eur_huf
    result["usd_huf"]   = usd_huf
    result["rate_date"] = rate_date

    # ── Determine comparison period and fetch comparison rates ─────────────────
    if weekday == 0:
        # Monday: compare last Friday vs the Friday before that
        # rate_date from API is Friday (latest settled trading day)
        if rate_date:
            friday_this  = rate_date  # API should return Friday's date on Monday
            friday_prev  = _get_friday_before(friday_this)
        else:
            friday_this  = _get_last_friday(now_budapest)
            friday_prev  = _get_friday_before(friday_this)
        prev_date = friday_prev
        result["comparison_label"] = "vs last Friday (week-over-week)"
        print(f"💱 Monday — fetching week-over-week comparison: {friday_prev}")
    else:
        # Tue–Sat: compare previous business day
        prev_date = _get_prev_business_day_from(rate_date) if rate_date else None
        result["comparison_label"] = "prev day"

    result["prev_date"] = prev_date

    if prev_date:
        print(f"💱 Fetching comparison rates ({prev_date}) for {result['comparison_label']}...")
        eur_huf_prev, usd_huf_prev, _, _ = _fetch_rates_with_fallback(prev_date, prev_date)
        result["eur_huf_prev"] = eur_huf_prev
        result["usd_huf_prev"] = usd_huf_prev
        if eur_huf_prev:
            print(f"  ✔️  Comparison: 1 EUR = {eur_huf_prev} HUF | 1 USD = {usd_huf_prev} HUF")

    # ── Calculate % change & volatility ──────────────────────────────────────
    VOLATILITY_THRESHOLD = 1.0

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

    # ── Build summary string ──────────────────────────────────────────────────
    if result["eur_huf"] and result["usd_huf"]:
        cmp_label = result["comparison_label"]

        trend_eur = ""
        if result["eur_change_pct"] is not None:
            sign = "+" if result["eur_change_pct"] >= 0 else ""
            trend_eur = f" ({sign}{result['eur_change_pct']}% {cmp_label})"

        trend_usd = ""
        if result["usd_change_pct"] is not None:
            sign = "+" if result["usd_change_pct"] >= 0 else ""
            trend_usd = f" ({sign}{result['usd_change_pct']}% {cmp_label})"

        date_label = f" [as of {result['rate_date']}'s close]" if result["rate_date"] else ""
        prev_label = f" [comparison: {result['prev_date']}]" if result["prev_date"] else ""

        result["summary"] = (
            f"1 EUR = {result['eur_huf']} HUF{trend_eur}{date_label} | "
            f"1 USD = {result['usd_huf']} HUF{trend_usd}{prev_label}"
        )
        volatility_label = "⚠️  HIGH VOLATILITY" if result["high_volatility"] else "✅ Low volatility"
        print(f"  {volatility_label} — {result['summary']}")

    return result


if __name__ == "__main__":
    rates = get_exchange_rates()
    print("\nFull result:")
    for k, v in rates.items():
        print(f"  {k}: {v}")
