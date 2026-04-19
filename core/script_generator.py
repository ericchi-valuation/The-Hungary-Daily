import os
import json
import time
import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def diagnostic_list_models(client):
    """
    [自動診斷工具] 查詢這把 API Key 到底可以使用哪些模型
    """
    print("\n🔍 [系統診斷] 正在向 Google 查詢此 API Key 可用的模型清單...")
    try:
        models = client.models.list()
        available_models = []
        for m in models:
            if 'generateContent' in m.supported_actions:
                clean_name = m.name.replace('models/', '')
                available_models.append(clean_name)
        
        if available_models:
            print(f"✅ 您的 API Key 支援以下 {len(available_models)} 個模型：")
            print(", ".join(available_models))
        else:
            print("❌ 警告：您的 API Key 無法存取任何文字生成模型！這通常是因為帳號權限或地區限制 (歐盟區)。")
            
    except Exception as e:
        print(f"❌ 查詢模型清單失敗，您的金鑰或連線被阻擋: {e}")
    print("-" * 50 + "\n")


def score_and_sort_articles(client, news_data):
    """
    使用 Gemini 1.5 Flash 快速為匈牙利新聞評分 (1-10)。
    """
    all_articles = []
    for source, articles in news_data.items():
        for a in articles:
            a['source_name'] = source
            all_articles.append(a)
    
    if not all_articles:
        return []

    articles_list_text = ""
    for i, a in enumerate(all_articles):
        articles_list_text += f"ID: {i} | Title: {a['title']}\nSummary: {a['summary']}\n\n"

    scoring_prompt = f"""
    You are an expert news editor for an English-language podcast in Hungary. 
    Score the following news articles from 1 to 10 based on their importance for international professionals and expats in Hungary.
    
    SCORING CRITERIA:
    - 8-10: Major economic shifts (HUF exchange rate, inflation), EU-Hungary political disputes (funding, rule of law), major foreign investments (BMW, CATL, battery plants), residency/visa rule changes.
    - 5-7: Significant tech/business news, major Budapest infrastructure updates, high-impact cultural events.
    - 1-4: Minor local news, general interest, lifestyle stories.
    
    IMPORTANT: If multiple articles discuss the same major topic, give them a "Frequency Bonus" (+1 or +2).
    
    OUTPUT FORMAT:
    You MUST output ONLY a raw JSON array. DO NOT wrap it in ```json blocks. DO NOT add any conversational text.
    Example:
    [
      {{"id": 0, "score": 8}},
      {{"id": 1, "score": 5}}
    ]
    
    ARTICLES:
    {articles_list_text}
    """

    try:
        print(f"正在為 {len(all_articles)} 則匈牙利新聞評分 (歐盟與匯率權重加持中)...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=scoring_prompt
        )
        
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        scores = json.loads(clean_text)
        
        score_map = {item['id']: item['score'] for item in scores}
        for i, a in enumerate(all_articles):
            a['score'] = score_map.get(i, 1)
            
    except Exception as e:
        print(f"⚠️ 評分階段發生錯誤: {e}")
        for a in all_articles:
            a['score'] = 1

    sorted_articles = sorted(all_articles, key=lambda x: x.get('score', 0), reverse=True)
    return sorted_articles[:10]


def generate_podcast_script(news_data, social_data):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("\n❌ Error: No valid GEMINI_API_KEY found.")
        return None

    client = genai.Client(api_key=api_key)

    # ==========================================
    # 在執行任何任務前，先印出您的專屬模型清單！
    # ==========================================
    diagnostic_list_models(client)

    top_articles = score_and_sort_articles(client, news_data)

    sources_text = "【Today's Prioritized Hungary News Headlines】\n"
    if not top_articles:
        sources_text += "No significant news articles found today.\n"
    else:
        for a in top_articles:
            sources_text += f"\n[Score: {a.get('score', 0)}/10] Source: {a.get('source_name')} | Title: {a.get('title')}\nSummary: {a.get('summary')}\n"

    sources_text += "\n\n【Hungary Social Media Trending (Reddit r/hungary + r/budapest + Facebook Expats)】\n"
    for post in social_data:
        title = post.get('title', 'Unknown Topic')
        topics = post.get('topics', [])
        topics_str = ', '.join(topics) if topics else 'General'
        sources_text += f"Topic: {title} (From {topics_str})\n"

    import pytz
    tz = pytz.timezone('Europe/Budapest')
    today_str = datetime.datetime.now(tz).strftime("%A, %B %d, %Y")

    system_prompt = f"""
    You are an energetic, professional yet engaging podcast host for a daily English-language news show
    called "The Hungarian Daily".

    Your strict target audience is: foreign professionals, expats, digital nomads, EU citizens, and 
    international business executives living or working in Budapest, Hungary.

    IMPORTANT: You MUST start every broadcast by warmly welcoming the listener and explicitly reading 
    today's date ({today_str}).

    ### MANDATORY SECTION — HUF EXCHANGE RATE ###
    You MUST include a dedicated "Currency Corner" segment in EVERY single broadcast, regardless of
    whether exchange rate news appears in today's headlines. This section is non-negotiable.
    - Report the approximate HUF/EUR and HUF/USD rates today (use the most recent data available in
      the source materials, or state a plausible current approximate figure if not explicitly provided).
    - Comment briefly on the trend (strengthening, weakening, stable) and what it means for expats:
      e.g., purchasing power, sending money abroad, salary calculations.
    - This segment should be about 150–200 words long.

    ### EDITORIAL GUIDELINES ###
    1. PRIORITIZATION: Maintain the order of the pre-sorted news items, leading with the highest-scoring stories.
    2. DEPTH: Devote significantly more time to higher-scoring stories (minimum 150 words per major story).
    3. EXPAT FOCUS: Prioritise EU-Hungary politics, HUF exchange rate, foreign investments, and visa changes.
    4. LANGUAGE: Present information naturally in English without mentioning the original language source.
    5. FILTER TRASH: Ignore tabloid gossip.
    6. SOCIAL MEDIA: Close the show with 1-2 quirky topics to explain Hungarian daily life.
    7. PRONUNCIATION: Write out difficult names phonetically (e.g., "Budapest" -> "Boo-da-pesht").
    8. TONE: Think "NPR Up First". Fast-paced, insightful, and end with a smile.
    9. LENGTH: The full script MUST be between 1800 and 2400 words — this produces an 8–12 minute episode
       at natural speaking pace. Do NOT submit a script shorter than 1800 words. If you are running short,
       add more depth, context, and analysis to the top stories. Pad with background on Hungary's economic
       situation or expat lifestyle tips — do NOT add filler words or repeat yourself.

    ### STRICT PROHIBITIONS ###
    - DO NOT include any Hungarian language lessons, "word of the day", vocabulary teaching, or phonetic
      coaching of Hungarian words/phrases. The TTS voice cannot pronounce Hungarian naturally, and such
      segments sound robotic and unprofessional. This is absolutely forbidden.
    - DO NOT teach listeners any Hungarian vocabulary, grammar, or language tips of any kind.
    - DO NOT use rhetorical sentence fragments as transitions. Fragments like "The central theme?",
      "The question?" or "The result?" followed by an answer are lazy writing that sounds odd when
      read aloud. Always write in complete, flowing sentences instead.
    - DO NOT state the wrong day of the week. Today is {today_str}. Use this exact date and day.

    ### SCRIPT FORMAT ###
    Output ONLY a JSON object. DO NOT wrap it in ```json blocks. 
    Format:
    {{
      "script": "The full spoken broadcast script...",
      "summary": "A concise 1-2 sentence summary..."
    }}
    """

    print("\n[AI Working] Synthesising Hungarian news and summary with Gemini (~20–40 sec)...")

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.6,
    )

    prompt_content = f"Here are today's materials. Please write the script and a summary:\n\n{sources_text}"

    # 這裡我們維持使用標準名稱
    models_to_try = ['gemini-2.5-flash', 'gemini-2.5-pro']
    response = None

    for model_name in models_to_try:
        retry_count = 0
        max_retries = 2
        
        while retry_count < max_retries:
            try:
                print(f"Trying model: {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt_content,
                    config=config
                )
                print(f"✔️  Content generated successfully with {model_name}!")
                break 
                
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️  {model_name} failed: {error_msg}")
                
                if "429" in error_msg or "Quota exceeded" in error_msg:
                    print("⏳ API Quota exhausted (429). Waiting 60 seconds before retrying...")
                    time.sleep(60)
                    retry_count += 1
                else:
                    break 

        if response:
            break 

    if getattr(response, 'text', None) is None:
        print("❌ All models failed to respond. Please check API status.")
        return None

    try:
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result_json = json.loads(clean_text)
        
        script = result_json.get('script', '')
        summary = result_json.get('summary', "Today's top news and updates from Hungary for expats.")

        with open("script.txt", "w", encoding="utf-8") as f:
            f.write(script)

        with open("summary.txt", "w", encoding="utf-8") as f:
            f.write(summary)

        print("✅ Script and summary ready! Saved to script.txt and summary.txt")
        return script

    except Exception as e:
        print(f"\n❌ Fatal error parsing JSON output: {e}\nModel returned:\n{response.text[:200]}...")
        return None