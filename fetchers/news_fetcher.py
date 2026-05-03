import feedparser
import time
from datetime import datetime, timezone, timedelta

# Basic blacklist to filter clickbait/tabloid headlines (LLM does a second pass)
GOSSIP_KEYWORDS = [
    'celebrity', 'scandal', 'affair', 'leaked', 'nude', 'nsfw',
    'clickbait', 'you won\'t believe', 'shocking truth', 'weird trick'
]

def is_trash_news(title, summary):
    text = (title + summary).lower()
    return any(kw in text for kw in GOSSIP_KEYWORDS)


def _is_recent(entry, max_hours=36):
    """
    Return True if the feed entry was published within the last `max_hours`.
    Uses published_parsed or updated_parsed from feedparser (UTC struct_time).
    Falls back to True if no date is present (to avoid over-filtering).

    36-hour window: captures today's news + yesterday evening (for early-morning runs).
    """
    for attr in ('published_parsed', 'updated_parsed'):
        t = getattr(entry, attr, None)
        if t is None:
            continue
        try:
            pub_utc = datetime(*t[:6], tzinfo=timezone.utc)
            cutoff  = datetime.now(timezone.utc) - timedelta(hours=max_hours)
            return pub_utc >= cutoff
        except Exception:
            continue

    return True  # no date info → include (don't silently drop undated feeds)


def fetch_rss_news(feed_url, limit=3, max_retries=3, max_hours=36):
    """Fetch articles from a single RSS source, filtered to the last `max_hours`."""
    entries = []

    for attempt in range(max_retries):
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return entries

            for entry in feed.entries:
                if len(entries) >= limit:
                    break

                # ── Date filter: skip stale articles ─────────────────────────
                if not _is_recent(entry, max_hours=max_hours):
                    continue

                title   = entry.get('title', 'No Title').strip()
                summary = entry.get('summary', entry.get('description', ''))

                if not title:
                    continue

                # Basic filter at crawler level
                if is_trash_news(title, summary):
                    continue

                entries.append({
                    'title':   title,
                    'summary': summary,
                    'link':    entry.get('link', '')
                })

            return entries

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print(f"Error parsing feed {feed_url}: {e}")
                return entries

    return entries


def get_daily_news(items_per_source=2):
    """
    Fetch news from Hungarian and international English-language sources.
    Only articles published within the last 36 hours are included,
    preventing stale/yesterday's news from polluting the script.

    Source mix:
    - English-language Hungarian media (for expat audience)
    - Hungarian-language domestic media (Gemini will read & synthesize into English)
    - Google News topic feeds for EU/economy context

    Target audience: foreign professionals, expats, EU citizens living/working in Hungary.
    """
    sources = {
        # --- English-language Hungarian media ---
        'Hungary Today (English)':          'https://hungarytoday.hu/feed',
        'Daily News Hungary (English)':     'https://dailynewshungary.com/feed/',
        'Budapest Business Journal (BBJ)':  (
            'https://news.google.com/rss/search?q=site:bbj.hu+when:2d'
            '&hl=en-HU&gl=HU&ceid=HU:en'
        ),
        'The Budapest Times (English)':     'https://budapesttimes.hu/feed',

        # --- Hungarian-language domestic media (AI synthesizes into English) ---
        'Telex.hu (Magyar – független)':         'https://telex.hu/rss',
        '444.hu (Magyar – ellenzéki)':           'https://444.hu/feed',
        'HVG.hu (Magyar – gazdaság/politika)':   'https://hvg.hu/rss',
        'Portfolio.hu (Magyar – pénzügy/piac)':  'https://www.portfolio.hu/rss/all.xml',

        # --- Additional Hungarian local media ---
        'Index.hu (Magyar – legnagyobb portál)': 'https://index.hu/24ora/rss/',
        'Origo.hu (Magyar – kormányközeli)':     'https://www.origo.hu/rss/origo.xml',
        'G7.hu (Magyar – gazdasági elemzés)':    'https://g7.hu/feed/',

        # --- Thematic Google News feeds (when:2d limits to 2 days) ---
        'Google News – Hungary Economy': (
            'https://news.google.com/rss/search?q=Hungary+economy+business+when:2d'
            '&hl=en-HU&gl=HU&ceid=HU:en'
        ),
        'Google News – Budapest City': (
            'https://news.google.com/rss/search?q=Budapest+news+today+when:2d'
            '&hl=en-HU&gl=HU&ceid=HU:en'
        ),
        'Google News – EU & Orbán Politics': (
            'https://news.google.com/rss/search?q=Hungary+Orban+EU+Visegrad+when:2d'
            '&hl=en&gl=US&ceid=US:en'
        ),
    }

    all_news = {}
    for source_name, url in sources.items():
        try:
            articles = fetch_rss_news(url, limit=items_per_source)
            if articles:
                all_news[source_name] = articles
        except Exception as e:
            print(f"Failed to fetch {source_name}: {e}")

    return all_news


if __name__ == "__main__":
    news = get_daily_news(2)
    for source, articles in news.items():
        print(f"--- {source} ---")
        for a in articles:
            print(f"  [{a['title']}]")
