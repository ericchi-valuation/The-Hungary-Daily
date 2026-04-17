import sys
import time
from fetchers.news_fetcher import get_daily_news
from fetchers.social_fetcher import get_social_trending
from core.script_generator import generate_podcast_script

def main():
    print("=" * 55)
    print("🎙️  The Hungarian Daily — Auto-Production System 🎙️")
    print("=" * 55)

    # -----------------------------------------------------------------
    # Stage 1: Gather raw material
    # -----------------------------------------------------------------
    print("\n[1/4] Crawling Hungarian news sources and social platforms...")
    time.sleep(1)

    news_data   = get_daily_news(items_per_source=3)
    social_data = get_social_trending(limit_per_source=3)

    total_news   = sum(len(articles) for articles in news_data.values())
    total_social = len(social_data)
    print(f"✔️  Collected {total_news} news articles and {total_social} social media posts.")

    # -----------------------------------------------------------------
    # Stage 2: AI editorial room — generate broadcast script
    # -----------------------------------------------------------------
    print("\n[2/4] Sending materials to AI editor to write the broadcast script...")
    script = generate_podcast_script(news_data, social_data)

    if not script:
        print("\nScript generation failed. Please check your API key or connection and retry.")
        sys.exit(1)

    # -----------------------------------------------------------------
    # Stage 3: Semi-automated safety valve → audio generation
    # -----------------------------------------------------------------
    print("\n" + "=" * 55)
    print("🚨  Safety checkpoint: draft saved to script.txt")
    print("👉  Review the script if needed, then the pipeline continues.")
    print("=" * 55)

    raw_voice_file = "HungaryDaily_Podcast.mp3"
    from core.audio_builder import build_podcast_audio
    build_podcast_audio(script_file="script.txt", output_file=raw_voice_file)

    # Post-production: mix in BGM
    from core.audio_mixer import mix_podcast_audio
    mix_podcast_audio(
        voice_file=raw_voice_file,
        bgm_file="bgm.mp3",
        output_file="HungaryDaily_Podcast_Final.mp3"
    )

    # -----------------------------------------------------------------
    # Stage 4: Content distribution (newsletter + Threads)
    # -----------------------------------------------------------------
    print("\n[4/4] Distributing content to newsletter and Threads...")
    from core.content_reformatter import reformat_for_newsletter, reformat_for_threads

    # Reformat for each channel
    newsletter_html = reformat_for_newsletter(script)
    threads_text    = reformat_for_threads(script)

    # Send newsletter
    from publishers.email_sender import send_newsletter
    import pytz
    import datetime
    tz_hu = pytz.timezone('Europe/Budapest')
    today_date = datetime.datetime.now(tz_hu).strftime("%Y-%m-%d")
    send_newsletter(f"The Hungarian Daily — {today_date}", newsletter_html)

    # Post to Threads
    from publishers.threads_poster import post_to_threads
    
    # 🌟 新增的 Debug 行：將 Threads 準備發布的內容印在 Log 裡
    print(f"\n👀 [Debug] Content prepared for Threads:\n{threads_text}\n" + "-" * 30)
    
    post_to_threads(threads_text)

    print("\n🎉  All automated tasks complete for today. Jó munkát! 🇭🇺")

if __name__ == "__main__":
    main()