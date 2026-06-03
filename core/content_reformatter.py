import os
from google import genai
from google.genai import types

def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def reformat_for_newsletter(podcast_script, events_data=None):
    """
    將原版廣播口語稿，改寫成排版精美、適合人眼閱讀的 HTML 電子報格式。
    如果提供了 events_data，會在電子報最後附加一個互動式的“Today in Budapest”活動區塊。
    """
    client = _get_gemini_client()
    if not client:
        return "<p>（無法生成電子報此內容，因為缺少 Gemini API Key）</p>"
        
    print("🤖 正在使用 AI 將廣播稿改寫為電子報 HTML 格式...")

    # 如果有事件資料，先在 Python 側組裝成 HTML，避免讓 LLM 虛構活動資訊
    events_html_block = ""
    if events_data:
        events_items = ""
        for ev in events_data:
            title   = ev.get('title', '').strip()
            summary = ev.get('summary', '').strip()
            link    = ev.get('link', '').strip()
            source  = ev.get('source', '').strip()
            if not title:
                continue
            link_tag = f' <a href="{link}" style="color:#e07b00;font-size:0.85em;">→ More info</a>' if link else ''
            events_items += (
                f'<li style="margin-bottom:10px;">'
                f'<strong>{title}</strong>{link_tag}'
                f'<br><span style="color:#555;font-size:0.9em;">{summary}</span>'
                f'<br><span style="color:#aaa;font-size:0.8em;">Source: {source}</span>'
                f'</li>'
            )
        if events_items:
            events_html_block = (
                '<hr style="margin:24px 0;">'
                '<h2 style="color:#b5451b;">&#127914; Today in Budapest</h2>'
                f'<ul style="padding-left:18px;">{events_items}</ul>'
                '<p style="margin-top:14px;font-size:0.9em;color:#444;">'
                '💬 <strong>Spotted something interesting happening in the city?</strong> '
                'Share it with us or reply to this email — we\'d love to feature community tips in future episodes!'
                '</p>'
            )
    
    prompt = f"""
    You are an expert tech and business newsletter editor. I'm providing you with a script that was designed to be read out loud as a podcast.
    Your task is to convert this spoken text into a clean, highly engaging HTML newsletter format.
    
    Requirements:
    1. Output ONLY valid HTML code. Do NOT output markdown formatting like ```html.
    2. Use semantic HTML tags: <h2> for main news topics, <ul>/<li> for bullet points, <strong> for emphasis.
    3. Remove any podcast-specific filler words (like "Welcome to the show", "I'm your host", "That wraps up our episode").
    4. Start immediately with: <h1>The Hungarian Daily</h1><p>Here are your top updates for today:</p>.
    5. Summarize the stories slightly if the spoken text is too verbose.
    6. Tone: Professional, forward-thinking, and easy to skim.
    7. At the very end of the HTML, after all news content, insert exactly this placeholder without modification: {{EVENTS_BLOCK}}
    8. After the events block placeholder, add a short sign-off paragraph in a <p> tag that says: "Enjoyed this briefing? Forward it to a friend in Budapest, or <a href='https://github.com/ericchi-valuation/The-Hungary-Daily'>subscribe to the podcast</a> to listen on the go."
    
    Here is the podcast script:
    {podcast_script}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        # Clean up any potential markdown code blocks returned by the model
        html_text = response.text.replace("```html", "").replace("```", "").strip()
        # Inject the pre-built events block (safe from hallucination)
        html_text = html_text.replace("{EVENTS_BLOCK}", events_html_block)
        return html_text
    except Exception as e:
        print(f"❌ 生成電子報內容失敗: {e}")
        return f"<p>生成電子報時發生錯誤: {podcast_script[:100]}...</p>"

def reformat_for_threads(podcast_script):
    """
    將原版廣播口語稿，改寫成精簡的社群貼文短語 (Threads 版)，必須嚴格少於 500 字元。
    """
    client = _get_gemini_client()
    if not client:
        return "New episode of The Hungarian Daily is live! Click the link in bio to listen 🎧"

    print("🤖 正在使用 AI 萃取 Threads 貼文精華短語...")
    
    # 強化版 Prompt：強制 AI 抓出具體新聞事件 (針對匈牙利頻道客製化)
    SPOTIFY_URL = "https://open.spotify.com/show/7zU2b8xDgRL8D7b9T9kjiE"
    prompt = f"""
    You are a witty, professional social media manager for an English-language news podcast about Hungary.
    Read the following podcast script and create a single post for Threads.
    
    CRITICAL REQUIREMENTS:
    1. You MUST include 2 or 3 bullet points summarizing the actual news headlines from the script (e.g., EU updates, HUF exchange rates, local tech). Do NOT just write generic teasers. Give me the facts.
    2. The entire output MUST be strictly UNDER 380 characters (we will add a Spotify link after).
    3. Use 1 or 2 relevant emojis.
    4. Do NOT use HTML formatting. Use plain text and line breaks.
    5. End the post with: "Listen now on Spotify 🎧" — that's the final line, no URL needed (we add it automatically).
    6. Do not include any title like "Threads Post:". Just return the text.
    7. IMPORTANT: Always say "today" not "this week". This is a DAILY podcast published every morning.
    
    Here is the podcast script:
    {podcast_script}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2, 
            )
        )
        result_text = response.text.strip()
        
        # 程式端附上 Spotify 連結（不靠AI，確保連結一定出現且正確）
        # 移除 AI 可能自行附上的連結重複字樣，再統一在結尾加上
        result_text = result_text.replace(SPOTIFY_URL, "").rstrip()
        result_text = f"{result_text}\n{SPOTIFY_URL}"
        
        # [Debug] 直接在 GitHub Log 印出來，方便我們抓蟲
        print("\n👀 [Debug] Gemini 生成的 Threads 貼文結果如下：")
        print("-" * 30)
        print(result_text)
        print(f"  (Total chars: {len(result_text)})")
        print("-" * 30 + "\n")
        
        return result_text
        
    except Exception as e:
        print(f"❌ Failed to generate Threads post: {e}")
        # 將備用字串加上標籤，方便辨識是否出錯
        return "[Auto-Gen Failed] New episode of The Hungarian Daily is live! Click the link to listen 🎧"