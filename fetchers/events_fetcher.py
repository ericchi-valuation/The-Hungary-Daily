"""
Budapest Events Fetcher
=======================
Fetches today's cultural, sports, and city events in Budapest from multiple
free/public sources. Returns a short list of highlights for the podcast script.

Sources used (all free, no API key required):
  1. Funzine.hu RSS             – English-language Budapest events guide
  2. We Love Budapest RSS        – Popular local lifestyle & events site
  3. Budapest.com Events RSS     – City event aggregator
  4. Google News (fallback)      – Search-based event discovery
"""

import feedparser
from datetime import datetime, timezone, timedelta
import pytz
import time

BUDAPEST_TZ = pytz.timezone("Europe/Budapest")


def _is_today_or_upcoming(entry, days_ahead=2):
    """
    Check if a feed entry is for today or within the next `days_ahead` days.
    Falls back to True if the entry has no parseable date (to avoid over-filtering).
    """
    now_budapest = datetime.now(BUDAPEST_TZ)
    cutoff_past  = now_budapest - timedelta(hours=12)  # allow events that started tonight
    cutoff_future = now_budapest + timedelta(days=days_ahead)

    # feedparser provides published_parsed / updated_parsed as UTC struct_time
    for attr in ('published_parsed', 'updated_parsed'):
        t = getattr(entry, attr, None)
        if t is None:
            continue
        try:
            dt_utc = datetime(*t[:6], tzinfo=timezone.utc)
            dt_bud = dt_utc.astimezone(BUDAPEST_TZ)
            return cutoff_past <= dt_bud <= cutoff_future
        except Exception:
            continue

    return True  # no date info → include by default


def _parse_feed(url, limit=4, label=""):
    """Fetch an RSS feed and return a list of event dicts."""
    events = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if len(events) >= limit:
                break
            if not _is_today_or_upcoming(entry):
                continue
            title   = entry.get("title", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()
            link    = entry.get("link", "")
            if not title:
                continue
            events.append({
                "title":   title,
                "summary": summary[:200] if summary else "",
                "link":    link,
                "source":  label,
            })
    except Exception as e:
        print(f"  ⚠️  Could not parse events feed ({label}): {e}")
    return events


def get_budapest_events(limit=3):
    """
    Aggregate today's Budapest events from multiple free RSS/web sources.
    Returns up to `limit` events suitable for inclusion in the podcast script.

    Each event dict has:
        title, summary, link, source
    """
    print("🎭 Fetching Budapest daily events...")
    all_events = []

    # ── Source 1: Funzine.hu (English events guide) ──────────────────────────
    all_events.extend(_parse_feed(
        "https://funzine.hu/feed/",
        limit=4,
        label="Funzine (English)"
    ))
    time.sleep(0.5)

    # ── Source 2: We Love Budapest (English lifestyle & events) ─────────────
    all_events.extend(_parse_feed(
        "https://welovebudapest.com/feed/",
        limit=4,
        label="We Love Budapest"
    ))
    time.sleep(0.5)

    # ── Source 3: Pestbuda.hu English section ────────────────────────────────
    all_events.extend(_parse_feed(
        "https://pestbuda.hu/feed/",
        limit=3,
        label="Pestbuda"
    ))
    time.sleep(0.5)

    # ── Source 4: Google News fallback ───────────────────────────────────────
    if len(all_events) < 2:
        google_url = (
            "https://news.google.com/rss/search"
            "?q=Budapest+event+concert+exhibition+festival+today"
            "&hl=en-HU&gl=HU&ceid=HU:en"
        )
        all_events.extend(_parse_feed(google_url, limit=3, label="Google News"))

    # ── Deduplicate by title (case-insensitive) ───────────────────────────────
    seen   = set()
    unique = []
    for ev in all_events:
        key = ev["title"].lower()[:60]
        if key not in seen:
            seen.add(key)
            unique.append(ev)

    # ── Return top N events ───────────────────────────────────────────────────
    selected = unique[:limit]
    if selected:
        print(f"  ✔️  Found {len(selected)} Budapest events:")
        for ev in selected:
            print(f"     • [{ev['source']}] {ev['title']}")
    else:
        print("  ⚠️  No Budapest events found today.")

    return selected


if __name__ == "__main__":
    events = get_budapest_events(limit=3)
    print("\n--- Budapest Events ---")
    for ev in events:
        print(f"[{ev['source']}] {ev['title']}")
        print(f"  {ev['summary'][:120]}")
        print(f"  {ev['link']}\n")
