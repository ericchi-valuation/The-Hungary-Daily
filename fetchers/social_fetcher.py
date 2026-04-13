import os
import requests
import feedparser
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REDDIT_HEADERS = {
    'User-Agent': 'HungaryDailyInsiderBot/1.0 (automated podcast; contact: ericchi.valuation@gmail.com)'
}

# ---------------------------------------------------------------------------
# Reddit r/hungary
# ---------------------------------------------------------------------------
def get_reddit_hungary(limit=3):
    """
    Fetch hot posts from r/hungary via Reddit's public JSON API (no OAuth needed).
    """
    url = "https://www.reddit.com/r/hungary/hot.json"
    try:
        resp = requests.get(url, headers=REDDIT_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        posts = []
        for child in data['data']['children']:
            post = child['data']
            # Skip stickied mod posts and very short/image-only posts
            if post.get('stickied'):
                continue
            title = post.get('title', '').strip()
            if not title:
                continue
            posts.append({
                'title': title,
                'url': 'https://www.reddit.com' + post.get('permalink', ''),
                'topics': ['Reddit r/hungary'],
                'score': post.get('score', 0)
            })
            if len(posts) >= limit:
                break
        return posts
    except Exception as e:
        print(f"Error fetching Reddit r/hungary: {e}")
        return []


# ---------------------------------------------------------------------------
# Reddit r/budapest
# ---------------------------------------------------------------------------
def get_reddit_budapest(limit=3):
    """
    Fetch hot posts from r/budapest – expat-heavy city-life discussions.
    """
    url = "https://www.reddit.com/r/budapest/hot.json"
    try:
        resp = requests.get(url, headers=REDDIT_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        posts = []
        for child in data['data']['children']:
            post = child['data']
            if post.get('stickied'):
                continue
            title = post.get('title', '').strip()
            if not title:
                continue
            posts.append({
                'title': title,
                'url': 'https://www.reddit.com' + post.get('permalink', ''),
                'topics': ['Reddit r/budapest'],
                'score': post.get('score', 0)
            })
            if len(posts) >= limit:
                break
        return posts
    except Exception as e:
        print(f"Error fetching Reddit r/budapest: {e}")
        return []


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
def get_social_trending(limit_per_source=2):
    """
    Aggregate trending social posts from:
      - Reddit r/hungary  (Hungarian public discussion)
      - Reddit r/budapest (Expat city-life topics)
      - Facebook – Hungary Expats group (optional, requires credentials)
    """
    posts = []
    posts.extend(get_reddit_hungary(limit=limit_per_source))
    posts.extend(get_reddit_budapest(limit=limit_per_source))
    posts.extend(get_fb_hungary_expats(limit=limit_per_source))
    return posts


if __name__ == "__main__":
    hot_topics = get_social_trending(limit_per_source=3)
    print("--- Hungary Social Trending (Reddit + Facebook Expats) ---")
    for topic in hot_topics:
        print(f"[{', '.join(topic['topics'])}] {topic['title']}")
        print(f"  URL: {topic['url']}\n")
