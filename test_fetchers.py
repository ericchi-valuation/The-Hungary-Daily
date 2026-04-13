from fetchers.news_fetcher import get_daily_news
from fetchers.social_fetcher import get_social_trending

def main():
    print("="*50)
    print("開始採集今日台灣新聞與社群素材...")
    print("="*50)
    
    # 1. 採集新聞
    news_data = get_daily_news(items_per_source=2)
    for source, articles in news_data.items():
        print(f"\n📰 來源: {source}")
        for i, article in enumerate(articles, 1):
            title = article['title']
            print(f"  {i}. {title}")
    
    print("\n" + "="*50)
    
    # 2. 採集社群熱門
    print("🔥 台灣社群熱門話題 (PTT + Dcard)")
    print("="*50)
    # Fix the argument name here
    social_posts = get_social_trending(limit_per_source=2)
    
    for i, post in enumerate(social_posts, 1):
        print(f"  {i}. {post['title']}")
        if post['topics']:
            print(f"     標籤: {', '.join(post['topics'][:3])}")

if __name__ == "__main__":
    main()
