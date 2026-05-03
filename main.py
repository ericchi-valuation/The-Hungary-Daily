import os

from core.content_reformatter import reformat_for_newsletter, reformat_for_threads

def verify_environment():
    """
    Check if all required environment variables are set.
    """
    required_keys = [
        "GEMINI_API_KEY",
        "ELEVENLABS_API_KEY",
        "GMAIL_ADDRESS",
        "GMAIL_APP_PASSWORD",
        "THREADS_USER_ID",
        "THREADS_ACCESS_TOKEN"
    ]
    missing = [key for key in required_keys if not os.getenv(key)]
    
    print("\n🔍 [Health Check] Verifying environment variables...")
    if missing:
        print(f"  ⚠️  Missing optional/required keys: {', '.join(missing)}")
        print("  (Pipeline will proceed but some steps may fail or fallback to free tiers)\n")
    else:
        print("  ✅ All environment variables are set.\n")

# ===========================================================================
# MAIN PIPELINE — this is the entry point called by GitHub Actions
# ===========================================================================
if __name__ == "__main__":
    import datetime
    import pytz
    from fetchers.news_fetcher import get_daily_news
    from fetchers.social_fetcher import get_social_trending
    from fetchers.weather_fetcher import get_budapest_weather
    from fetchers.exchange_rate_fetcher import get_exchange_rates
    from fetchers.events_fetcher import get_budapest_events
    from core.script_generator import generate_podcast_script, review_and_improve_script
    from core.audio_builder import build_podcast_audio
    from core.audio_mixer import mix_podcast_audio
    from publishers.email_sender import send_newsletter
    from publishers.threads_poster import post_to_threads

    verify_environment()

    tz_str = os.environ.get("TZ", "Europe/Budapest")
    tz = pytz.timezone(tz_str)
    today_str = datetime.datetime.now(tz).strftime("%B %d, %Y")

    print("=" * 60)
    print(f"🎙️  The Hungarian Daily — Pipeline starting for {today_str}")
    print("=" * 60)

    # ── Step 1: Fetch news, weather & social data ──────────────────────────────────────────
    print("\n📡 Step 1/5: Fetching latest Hungarian news...")
    news_data = get_daily_news(items_per_source=2)
    print(f"  ✔️ Collected articles from {len(news_data)} sources.")

    print("\n🌤️  Step 1b: Fetching Budapest weather...")
    weather_data = get_budapest_weather()

    print("\n💱  Step 1c: Fetching Exchange Rates...")
    exchange_data = get_exchange_rates()

    print("\n💬 Step 1d: Fetching social trending topics...")
    social_data = get_social_trending(limit_per_source=2)
    print(f"  ✔️ Collected {len(social_data)} social trending posts.")

    print("\n🎭 Step 1e: Fetching Budapest events...")
    events_data = get_budapest_events(limit=2)

    # ── Step 1f: Read Sponsor Text ──────────────────────────────────────────
    sponsor_text = None
    if os.path.exists("sponsor.txt"):
        try:
            with open("sponsor.txt", "r", encoding="utf-8") as f:
                sponsor_text = f.read().strip()
            if sponsor_text:
                print(f"  ✔️  Sponsor text detected: '{sponsor_text[:30]}...'")
        except Exception as e:
            print(f"  ⚠️  Could not read sponsor.txt: {e}")

    # ── Step 2: Generate AI podcast script ──────────────────────────────────────────
    print("\n🤖 Step 2/5: Generating AI podcast script...")
    script = generate_podcast_script(
        news_data, 
        social_data, 
        weather_data, 
        exchange_data, 
        events_data, 
        sponsor_text=sponsor_text
    )

    if not script:
        print("❌ Script generation failed. Aborting pipeline.")
        raise SystemExit(1)

    print(f"  ✔️ Script generated ({len(script.split())} words).")

    # ── Step 2b: AI Editor 審稿 —————————————————————————————──
    print("\n📝 Step 2b/5: AI Editor reviewing script before TTS...")
    script = review_and_improve_script(script)

    # 將審稿後的最終稿件寫回 script.txt
    with open("script.txt", "w", encoding="utf-8") as f:
        f.write(script)
    print(f"  ✔️ Final script saved ({len(script.split())} words). Ready for TTS.")

    # ── Step 3: Build TTS audio ──────────────────────────────────────
    print("\n🎤 Step 3/5: Generating TTS audio from script...")
    VOICE_FILE = "HungaryDaily_Podcast.mp3"
    FINAL_FILE = "HungaryDaily_Podcast_Final.mp3"
    BGM_FILE   = "bgm.mp3"

    build_podcast_audio(script_file="script.txt", output_file=VOICE_FILE)

    if not os.path.exists(VOICE_FILE) or os.path.getsize(VOICE_FILE) == 0:
        print("❌ TTS audio not generated. Aborting pipeline.")
        raise SystemExit(1)

    print(f"  ✔️ Raw voice audio ready: {VOICE_FILE}")

    # ── Step 4: Mix BGM with voice ────────────────────────────────────
    print("\n🎵 Step 4/5: Mixing BGM with voice...")
    if os.path.exists(BGM_FILE):
        try:
            mix_podcast_audio(
                voice_file=VOICE_FILE,
                bgm_file=BGM_FILE,
                output_file=FINAL_FILE
            )
            print(f"  ✔️ Final mixed podcast ready: {FINAL_FILE}")
        except Exception as e:
            print(f"  ⚠️ Mixing failed ({e}). Falling back to voice-only file.")
            import shutil
            shutil.copy(VOICE_FILE, FINAL_FILE)
    else:
        print(f"  ⚠️ BGM file '{BGM_FILE}' not found. Using voice-only output.")
        import shutil
        shutil.copy(VOICE_FILE, FINAL_FILE)

    # ── Step 5: Publish ─────────────────────────────────────────────
    print("\n📢 Step 5/5: Publishing content...")

    # 5a. Newsletter
    try:
        with open("script.txt", "r", encoding="utf-8") as f:
            script_text = f.read()
        html_content = reformat_for_newsletter(script_text)
        subject = f"The Hungarian Daily — {today_str}"
        send_newsletter(subject, html_content)
    except Exception as e:
        print(f"  ⚠️ Newsletter step failed: {e}")

    # 5b. Threads
    try:
        with open("script.txt", "r", encoding="utf-8") as f:
            script_text = f.read()
        threads_post = reformat_for_threads(script_text)
        post_to_threads(threads_post)
    except Exception as e:
        print(f"  ⚠️ Threads step failed: {e}")

    print("\n" + "=" * 60)
    print(f"✅ Pipeline complete! '{FINAL_FILE}' is ready for upload.")
    print("=" * 60)