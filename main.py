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
    2. STRICT FACTUALITY: Do NOT invent, hallucinate, or assume any numbers, dates, stock prices, or exchange rates (like HUF/EUR). ONLY use facts and figures explicitly stated in the script. If the script doesn't mention a number, do NOT add one.
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
