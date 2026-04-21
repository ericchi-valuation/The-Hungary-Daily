import os
from google import genai
from google.genai import types

def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def reformat_for_newsletter(podcast_script):
    """
    將原版廣播口語稿，改寫成排版精美、適合人眼閱讀的 HTML 電子報格式。
    """
    client = _get_gemini_client()
    if not client:
        return "<p>（無法生成電子報此內容，因為缺少 Gemini API Key）</p>"
        
    print("🤖 正在使用 AI 將廣播稿改寫為電子報 HTML 格式...")
    
    prompt = f"""
    You are an expert tech and business newsletter editor. I'm providing you with a script that was designed to be read out loud as a podcast.
    Your task is to convert this spoken text into a clean, highly engaging HTML newsletter format.
    
    Requirements:
    1. Output ONLY valid HTML code. Do NOT output markdown formatting like ```html.
    2. Use semantic HTML tags: <h2> for main news topics, <ul>/<li> for bullet points, <strong> for emphasis.
    3. Remove any podcast-specific filler words (like "Welcome to the show", "I'm your host", "That wraps up our episode").
    4. Start immediately with a friendly greeting directly formatted in HTML, e.g., <h1>The Hungarian Daily</h1><p>Here are your top updates for today:</p>.
    5. Summarize the stories slightly if the spoken text is too verbose.
    6. Tone: Professional, forward-thinking, and easy to skim.
    
    Here is the podcast script:
    {podcast_script}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        html_text = response.text.replace("```html", "").replace("```", "").strip()
        return html_text
    except Exception as e:
        print(f"❌ 生成電子報內容失敗: {e}")
        return f"<p>生成電子報時發生錯誤: {podcast_script[:100]}...</p>"

def reformat_for_threads(podcast_script):
    """
    將原版廣播口語稿，改寫成精簡的社群貼文短語 (Threads 版)，並嚴格防範幻覺。
    """
    client = _get_gemini_client()
    if not client:
        return "New episode of The Hungarian Daily is live! Click the link in bio to listen 🎧"

    print("🤖 正在使用 Pro 模型與低溫設定，嚴謹萃取 Threads 貼文精華...")
    
    prompt = f"""
    You are a witty, professional social media manager for an English-language news podcast about Hungary.
    Read the following podcast script and create a single post for Threads.
    
    CRITICAL REQUIREMENTS:
    1. You MUST include 2 or 3 bullet points summarizing the actual news headlines from the script.
    2. STRICT FACTUALITY: Do NOT invent, hallucinate, or assume any numbers, dates, stock prices,
       exchange rates (like HUF/EUR or HUF/USD) or weather figures.
       ONLY use facts and figures EXPLICITLY stated word-for-word in the script.
       If the script does not mention a number, you MUST NOT include that number. Period.
    3. The entire output MUST be strictly UNDER 450 characters (leave some room for hashtags).
    4. Use 1 or 2 relevant emojis.
    5. Do NOT use HTML formatting. Use plain text and line breaks.
    6. End the post with a call-to-action like "Listen to the full episode on our feed! 🎧".
    7. Do not include any title/heading like "Threads Post:". Just return the text.
    
    Here is the podcast script:
    {podcast_script}
    """

    try:
        # 換上最強邏輯模型並降低溫度
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2, 
            )
        )
        result_text = response.text.strip()
        
        print("\n👀 [Debug] Gemini Pro 生成的 Threads 貼文結果如下：")
        print("-" * 30)
        print(result_text)
        print("-" * 30 + "\n")
        
        return result_text
        
    except Exception as e:
        print(f"❌ Failed to generate Threads post: {e}")
        return "[Auto-Gen Failed] New episode of The Hungarian Daily is live! Click the link to listen 🎧"


# ===========================================================================
# MAIN PIPELINE — this is the entry point called by GitHub Actions
# ===========================================================================
if __name__ == "__main__":
    import datetime
    import pytz
    from fetchers.news_fetcher import get_daily_news
    from fetchers.social_fetcher import get_social_trending
    from fetchers.weather_fetcher import get_budapest_weather
    from core.script_generator import generate_podcast_script
    from core.audio_builder import build_podcast_audio
    from core.audio_mixer import mix_podcast_audio
    from publishers.email_sender import send_newsletter
    from publishers.threads_poster import post_to_threads

    tz = pytz.timezone('Europe/Budapest')
    today_str = datetime.datetime.now(tz).strftime("%B %d, %Y")

    print("=" * 60)
    print(f"🎙️  The Hungarian Daily — Pipeline starting for {today_str}")
    print("=" * 60)

    # ── Step 1: Fetch news, weather & social data ──────────────────────────────────────────
    print("\n📡 Step 1/5: Fetching latest Hungarian news...")
    news_data = get_daily_news(items_per_source=3)
    print(f"  ✔️ Collected articles from {len(news_data)} sources.")

    print("\n🌤️  Step 1b: Fetching Budapest weather...")
    weather_data = get_budapest_weather()

    print("\n💬 Step 1c: Fetching social trending topics...")
    social_data = get_social_trending(limit_per_source=2)
    print(f"  ✔️ Collected {len(social_data)} social trending posts.")

    # ── Step 2: Generate AI podcast script ──────────────────────────────────────────
    print("\n🤖 Step 2/5: Generating AI podcast script...")
    script = generate_podcast_script(news_data, social_data, weather_data)

    if not script:
        print("❌ Script generation failed. Aborting pipeline.")
        raise SystemExit(1)

    print(f"  ✔️ Script generated ({len(script.split())} words).")

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