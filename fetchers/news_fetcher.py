import feedparser

# Basic blacklist to filter clickbait/tabloid headlines (LLM does a second pass)
GOSSIP_KEYWORDS = [
    'celebrity', 'scandal', 'affair', 'leaked', 'nude', 'nsfw',
    'clickbait', 'you won\'t believe', 'shocking truth', 'weird trick'
]

def is_trash_news(title, summary):
    text = (title + summary).lower()
    return any(kw in text for kw in GOSSIP_KEYWORDS)

def fetch_rss_news(feed_url, limit=3):
    """Fetch articles from a single RSS source."""
    feed = feedparser.parse(feed_url)
    entries = []

    if not feed.entries:
        return entries

    for entry in feed.entries:
        if len(entries) >= limit:
            break

        title = entry.get('title', 'No Title').strip()
        summary = entry.get('summary', entry.get('description', ''))

        if not title:
            continue

        # Basic filter at crawler level
        if is_trash_news(title, summary):
            continue

        entries.append({
            'title': title,
            'summary': summary,
            'link': entry.get('link', '')
        })
    return entries

def get_daily_news(items_per_source=2):
    """
    Fetch news from Hungarian and international English-language sources.

    Source mix:
    - English-language Hungarian media (for expat audience)
    - Hungarian-language domestic media (Gemini will read & synthesize into English)
    - Google News topic feeds for EU/economy context
    
    Target audience: foreign professionals, expats, EU citizens living/working in Hungary.
    """
    sources = {
        # --- English-language Hungarian media ---
        'Hungary Today (English)': 'https://hungarytoday.hu/feed',
        'Daily News Hungary (English)': 'https://dailynewshungary.com/feed/',
        'Budapest Business Journal (BBJ)': (
            'https://news.google.com/rss/search?q=site:bbj.hu+when:2d'
            '&hl=en-HU&gl=HU&ceid=HU:en'
        ),
        'The Budapest Times (English)': 'https://budapesttimes.hu/feed',

        # --- Hungarian-language domestic media (AI synthesizes into English) ---
        'Telex.hu (Magyar – független)':   'https://telex.hu/rss',
        '444.hu (Magyar – ellenzéki)':     'https://444.hu/feed',
        'HVG.hu (Magyar – gazdaság/politika)': 'https://hvg.hu/rss',
        'Portfolio.hu (Magyar – pénzügy/piac)': 'https://www.portfolio.hu/rss/all.xml',

        # --- Additional Hungarian local media (wider coverage & political balance) ---
        'Index.hu (Magyar – legnagyobb portál)': 'https://index.hu/24ora/rss/',
        'Origo.hu (Magyar – kormányközeli)': 'https://www.origo.hu/rss/origo.xml',
        'G7.hu (Magyar – gazdasági elemzés)': 'https://g7.hu/feed/',
        # --- Thematic Google News feeds ---
        'Google News – Hungary Economy': (
            'https://news.google.com/rss/search?q=Hungary+economy+business'
            '&hl=en-HU&gl=HU&ceid=HU:en'
        ),
        'Google News – Budapest City': (
            'https://news.google.com/rss/search?q=Budapest+news+today'
            '&hl=en-HU&gl=HU&ceid=HU:en'
        ),
        'Google News – EU & Orbán Politics': (
            'https://news.google.com/rss/search?q=Hungary+Orban+EU+Visegrad'
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
