import os
import requests
import feedparser
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Reddit Bypass (via Google News RSS)
# ---------------------------------------------------------------------------
def get_reddit_trending_bypassed(subreddit, limit=3):
    """
    Bypasses Reddit's 403/block by searching for the subreddit content on Google News RSS.
    This is highly reliable for GitHub Actions runners.
    """
    query = f"site:reddit.com/r/{subreddit}+when:1d"
    url = f"https://news.google.com/rss/search?q={query}&hl=en-HU&gl=HU&ceid=HU:en"
    
    try:
        feed = feedparser.parse(url)
        posts = []
        for entry in feed.entries[:limit]:
            title = entry.get('title', '').split(' - r/')[0].strip()
            posts.append({
                'title': title,
                'url': entry.get('link', ''),
                'topics': [f'Reddit r/{subreddit}']
            })
        return posts
    except Exception as e:
        print(f"Error fetching Reddit r/{subreddit} (Bypassed): {e}")
        return []

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def get_social_trending(limit_per_source=2):
    """
    Aggregate trending social posts from:
      - Reddit r/hungary  (via Google News Bypass)
      - Reddit r/budapest (via Google News Bypass)
      - Facebook – Hungary Expats group (optional)
    """
    posts = []
    posts.extend(get_reddit_trending_bypassed('hungary', limit=limit_per_source))
    posts.extend(get_reddit_trending_bypassed('budapest', limit=limit_per_source))
    posts.extend(get_fb_hungary_expats(limit=limit_per_source))
    return posts


# ---------------------------------------------------------------------------
# Facebook – Hungary Expats group (via Graph API, optional)
# ---------------------------------------------------------------------------
def get_fb_hungary_expats(limit=3):
    """
    Fetch recent posts from the 'Hungary Expats' Facebook group using the 
    Facebook Graph API.

    Requires two environment variables:
      FB_GROUP_ID          – The numeric ID of the Hungary Expats group
      FB_ACCESS_TOKEN      – A long-lived User or Page access token with
                             groups_access_member_info / public_groups scope

    If either variable is missing the function silently returns an empty list,
    so the pipeline degrades gracefully without crashing.
    """
    group_id    = os.environ.get("FB_GROUP_ID", "")
    access_token = os.environ.get("FB_ACCESS_TOKEN", "")

    if not group_id or not access_token or access_token == "your_fb_access_token_here":
        print("⚠️  FB_GROUP_ID / FB_ACCESS_TOKEN not set – skipping Facebook source.")
        return []

    url = f"https://graph.facebook.com/v19.0/{group_id}/feed"
    params = {
        "fields": "message,story,permalink_url,created_time",
        "limit": limit * 2,   # fetch extra to compensate for posts with no message text
        "access_token": access_token
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        posts = []
        for item in data.get('data', []):
            text = (item.get('message') or item.get('story') or '').strip()
            if not text:
                continue
            # Use first ~120 chars as the "title" so it blends into the social segment
            title = text[:120].replace('\n', ' ')
            posts.append({
                'title': title,
                'url': item.get('permalink_url', ''),
                'topics': ['Facebook – Hungary Expats']
            })
            if len(posts) >= limit:
                break
        return posts
    except Exception as e:
        print(f"Error fetching Facebook Hungary Expats: {e}")
        return []


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
# (Integrated at the top)


if __name__ == "__main__":
    hot_topics = get_social_trending(limit_per_source=3)
    print("--- Hungary Social Trending (Reddit + Facebook Expats) ---")
    for topic in hot_topics:
        print(f"[{', '.join(topic['topics'])}] {topic['title']}")
        print(f"  URL: {topic['url']}\n")
