import os
import json
import time
import datetime
import re
import pytz
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
    - 9-10: Major political crises with direct economic impact on Hungary, EU-Hungary funding disputes or breakthroughs, HUF currency crashes (>1% move), major geopolitical events WITH DIRECT HUNGARY NEXUS.
    - 7-8: Significant Hungarian business/investment news (BMW, CATL, major foreign investment), genuine NEW immigration policy changes (new law passed, new visa category announced — NOT weekly newsletters or company updates), major Budapest city decisions.
    - 5-6: General economic data (GDP, trade), EU policy updates with moderate Hungary relevance, notable Budapest lifestyle or cultural events.
    - 2-4: Minor local news, general interest stories.
    - 1-3: AUTOMATIC LOW SCORE — (a) Commercial press releases from immigration consulting firms (Crown World Mobility, KPMG, Deloitte immigration newsletters, etc.) (b) Global geopolitical conflicts with NO direct Hungary connection (e.g. Israel-Iran war, US domestic politics, Middle East tensions) — mention these only briefly as international context, never as a top story. (c) "Weekly update" roundups from private companies. These are NOT primary news.
    
    KEY AUDIENCE CONTEXT: Listeners are EU Blue Card holders and senior foreign professionals already living and working legally in Budapest. They care most about: Hungary economy, HUF stability, major policy shifts, business environment, and Budapest life. Global conflict news that doesn't directly affect Hungary should be ONE brief sentence of context, not a lead story.
    
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

    # 定義 JSON Schema
    scoring_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "id": {"type": "INTEGER"},
                "score": {"type": "INTEGER"}
            },
            "required": ["id", "score"]
        }
    }

    # 評分用的備援模型清單（依照 API Key 診斷結果排列）
    # 已移除: gemini-2.0-flash-001 (已下架 404)
    scoring_models = ['gemini-2.5-flash', 'gemini-3.5-flash', 'gemini-2.5-flash-lite']
    scores = None

    for scoring_model in scoring_models:
        try:
            print(f"正在為 {len(all_articles)} 則匈牙利新聞評分 (模型: {scoring_model})...")
            response = client.models.generate_content(
                model=scoring_model,
                contents=scoring_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=scoring_schema
                )
            )

            if response.parsed:
                scores = response.parsed
            else:
                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                json_match = re.search(r'\[.*\]', clean_text, re.DOTALL)
                if json_match:
                    clean_text = json_match.group(0)
                scores = json.loads(clean_text)
            print(f"  ✔️ 評分完成 (使用 {scoring_model})")
            break  # 成功，跳出迴圈

        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ 評分階段發生錯誤 ({scoring_model}): {e}")
            # 503 = 暫時過載，稍等後嘗試下一個模型
            if "503" in error_msg or "UNAVAILABLE" in error_msg:
                print("  ⏳ API 暫時過載 (503)，等待 15 秒後換用備援模型...")
                time.sleep(15)
            continue

    if scores is None:
        print("⚠️ 所有評分模型均失敗，改用預設分數繼續流程。")
        for a in all_articles:
            a['score'] = 1
    else:
        score_map = {item['id']: item['score'] for item in scores}
        for i, a in enumerate(all_articles):
            a['score'] = score_map.get(i, 1)

    sorted_articles = sorted(all_articles, key=lambda x: x.get('score', 0), reverse=True)
    return sorted_articles[:10]


def generate_podcast_script(news_data, social_data, weather_data=None, exchange_data=None, events_data=None, sponsor_text=None):
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

    sources_text += "\n\n[🌤️ Today's Budapest Weather Forecast]》\n"
    if weather_data and weather_data.get('condition') != 'Data unavailable':
        sources_text += (
            f"Condition: {weather_data.get('condition')}\n"
            f"High: {weather_data.get('temp_max_c')}°C / {weather_data.get('temp_max_f')}°F\n"
            f"Low: {weather_data.get('temp_min_c')}°C / {weather_data.get('temp_min_f')}°F\n"
            f"Wind: up to {weather_data.get('wind_kmh')} km/h\n"
            f"Precipitation: {weather_data.get('precip_mm')} mm\n"
        )
    else:
        sources_text += "Weather data unavailable today.\n"

    if exchange_data and exchange_data.get('eur_huf'):
        sources_text += "\n\n[💱 Today's Exchange Rates]》\n"
        sources_text += f"High Volatility: {'YES' if exchange_data.get('high_volatility') else 'NO'}\n"
        sources_text += exchange_data.get('summary', '') + "\n"

    sources_text += "\n\n《💬 Hungary Social Media Trending (Reddit r/hungary + r/budapest + Facebook Expats)》\n"
    for post in social_data:
        title = post.get('title', 'Unknown Topic')
        topics = post.get('topics', [])
        topics_str = ', '.join(topics) if topics else 'General'
        sources_text += f"Topic: {title} (From {topics_str})\n"

    if events_data:
        sources_text += "\n\n[🎭 Today's Budapest Events]》\n"
        for ev in events_data:
            sources_text += f"Event: {ev.get('title')} (Source: {ev.get('source')})\nSummary: {ev.get('summary')}\n"

    tz_str = os.environ.get("TZ", "Europe/Budapest")
    tz = pytz.timezone(tz_str)
    today_str = datetime.datetime.now(tz).strftime("%A, %B %d, %Y")

    sponsor_instruction = ""
    if sponsor_text and sponsor_text.strip():
        sponsor_instruction = f"This episode is sponsored by: {sponsor_text.strip()}."
    else:
        sponsor_instruction = "This episode has no current sponsor. Do NOT mention a sponsor."

    system_prompt = f"""
    You are Ray, an energetic, professional yet engaging podcast host for a daily English-language news show
    called "The Hungarian Daily".

    Your strict target audience is: EU Blue Card holders, senior foreign professionals, and international business executives already living and working legally in Budapest, Hungary. They have their work permits sorted. They primarily care about the economy, business environment, HUF stability, major policy shifts, and quality of life in Budapest.

    IMPORTANT: You MUST start every broadcast by warmly welcoming the listener, introducing yourself as Ray,
    explicitly reading today's date ({today_str}), and integrating the sponsor message if provided.
    
    ### SPONSOR MESSAGE ###
    {sponsor_instruction}
    - If a sponsor is provided, mention it naturally early in the show.
    - If NO sponsor is provided, skip the sponsor mention entirely.

    ### MANDATORY SECTION — WEATHER BRIEFING ###
    Immediately after the opening, include a short "Budapest Weather Briefing" segment.
    - Use the weather data provided. Report high/low in both Celsius and Fahrenheit.
    - Give a brief lifestyle tip (e.g., "bring an umbrella").

    ### MANDATORY SECTION — SMART CURRENCY CORNER ###
    Next, include the "Currency Corner".
    - CRITICAL TIMING CONTEXT: The exchange rates come from the last available settled trading day's closing rates — NOT real-time.
    - When announcing rates, always frame accurately: "As of the last market close" or "The latest settled closing rate from [date]."
      NEVER say "Today's exchange rate is X" or "right now."
    - Report the exact HUF/EUR and HUF/USD rates provided.
    - SMART LOGIC: If "High Volatility: YES" — give deeper analysis of the swing and its impact. If "High Volatility: NO" — keep it VERY brief: state the rates and say "The Forint is stable."
    - SUNDAY RULE: If the exchange rate summary says "SUNDAY_NO_RATES", SKIP the Currency Corner segment entirely. Do not mention exchange rates at all. Sunday markets are closed.
    - MONDAY RULE: If "is_monday: True" and a week-over-week comparison is provided, frame it as: "Looking back at the week, the Forint ended last Friday at [rate], compared to [rate] the Friday before — a [X]% move over the week." This gives listeners a weekly performance overview instead of a daily blip.

    ### EDITORIAL GUIDELINES ###
    1. PRIORITIZATION: Maintain the order of the pre-sorted news items.
    
    2. IMMIGRATION NEWS — PROPORTIONAL COVERAGE: Only cover immigration if there is a GENUINE new government policy announcement (a new law, a new visa category, a rule change). Do NOT give prominent coverage to routine weekly updates from immigration consulting firms (e.g. Crown World Mobility), advisory company newsletters, or minor procedural notices. Mention such sources in one sentence at most, or skip them entirely.
    
    3. GLOBAL NEWS WITHOUT HUNGARY NEXUS — BRIEF ONLY: If a top story is a global conflict or geopolitical event with NO direct Hungary connection (e.g. Israel-Iran war, US elections, Middle East tensions), cover it in 2-3 sentences maximum as an "international briefing" context note. Do NOT build it into a full segment or lead story. Always connect it back to Hungary: "For context, global oil prices may affect Hungary's energy costs..."
    
    4. NO REPETITIVE ANALYSIS — CRITICAL RULE: Each news story gets ONE clear, concise treatment. Structure: (a) What happened, (b) What it means for the listener — maximum 4 sentences total per story. DO NOT write a second paragraph that restates the same analysis with slightly different wording. DO NOT add a "historical context" paragraph that just repeats what you just said. This is the most common AI padding mistake and it is BANNED.
    
    5. MISSING EXCHANGE RATE DATA: If today's exchange rate data is unavailable, do NOT say "we have no data" on air. Instead say: "The Forint continues to trade in the range we saw earlier this week — we'll bring you the latest settled figures as soon as markets close." Keep it professional and brief.
    
    6. DEPTH: Devote more time to high-scoring stories through genuine analysis, not through repetition.
    
    7. FACT-CHECKING — STALE NEWS: Check publication dates. If an event already happened (e.g. a concert that ended 3 days ago, a competition that concluded last week), do NOT present it as upcoming or current. Either skip it or use past tense: "Budapest hosted..."
    
    8. EVENTS: After the news, feature 1-2 interesting Budapest events. Only include UPCOMING or CURRENT events, never past events. Describe them briefly.
    
    9. SOCIAL MEDIA: Include 1 quirky social media topic after events.
    
    10. CALL TO ACTION (CTA): MANDATORY closing: "That's all for today's Hungarian Daily. If you enjoyed this episode, please subscribe, share it with friends and colleagues in Budapest, and drop us a review wherever you listen — it really helps. I'm Ray, and I'll see you tomorrow. Viszlát!"
    
    11. TONE: Think "NPR Up First". Fast-paced, punchy, confident. Say things once, say them well.
    
    12. LENGTH: The full script MUST be between 1800 and 2400 words. To add length WITHOUT repeating yourself: add genuine analysis, explain the wider economic implications, or give relevant background on Hungary. NEVER pad by repeating the same story twice in different words.
    13. POLITICAL TITLES — TWO-TIER FACT-CHECK RULE:

        TIER 1 — VERIFIED CURRENT LEADERS LIST (use these titles even if a source has an error):
        The following leaders are confirmed in office as of early 2025 and should retain their titles
        unless today's source material EXPLICITLY says they resigned or were removed:
          • Donald Trump = "US President" or "President Trump" (47th US President, inaugurated Jan 20, 2025).
            NEVER call him "former President" — that is factually wrong as of 2025-2026.
          • Friedrich Merz = "German Chancellor" (took office February 2025).
          • Emmanuel Macron = "French President".
          • Ursula von der Leyen = "European Commission President".

        TIER 2 — ALL OTHER POLITICAL FIGURES: NEVER assume a title from training data.
        ONLY use titles (e.g. "Prime Minister", "Minister of Finance") that are EXPLICITLY stated
        in TODAY's provided source materials. If a source calls someone "Prime Minister X" but
        other signals suggest they may no longer hold that role, use their NAME ONLY
        (e.g. "Viktor Orbán stated...") and note "according to [source]."
        SPECIFIC NOTE: Do NOT refer to Viktor Orbán as Hungary's Prime Minister unless today's
        source materials explicitly confirm he currently holds that office.

    ### STRICT PROHIBITIONS ###
    - DO NOT include Hungarian language lessons.
    - DO NOT use rhetorical sentence fragments.
    - DO NOT use any Markdown formatting.
    - DO NOT invent numbers or exchange rates.
    - DO NOT mention any editorial score or rating in the spoken script (e.g. "scoring 9 out of 10", "a score of 8", "rated 7/10"). Scores are internal editorial tools only and must never appear in the broadcast.
    - DO NOT list or enumerate the target audience by name in the script. Phrases like "our community of foreign professionals, expats, digital nomads, and international executives" or any similar enumeration of listener types are BANNED. Speak directly to the listener as "you" instead.

    ### SCRIPT FORMAT ###
    Output ONLY a JSON object.
    Format:
    {{
      "script": "The full spoken broadcast script ending with the mandatory CTA and Viszlát sign-off...",
      "summary": "A 3-5 sentence episode description for podcast platforms. Start with today's top 2-3 news stories, then list today's Budapest events with their names and a one-line description each. End with one sentence inviting listeners to tune in."
    }}
    """

    # 定義 JSON Schema
    podcast_schema = {
        "type": "OBJECT",
        "properties": {
            "script": {"type": "STRING"},
            "summary": {"type": "STRING"}
        },
        "required": ["script", "summary"]
    }

    print("\n[AI Working] Synthesising Hungarian news and summary with Gemini (~20–40 sec)...")

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.6,
        response_mime_type='application/json',
        response_schema=podcast_schema
    )

    prompt_content = f"Here are today's materials. Please write the script and a summary:\n\n{sources_text}"

    # 主要生成模型清單（已移除下架的 gemini-2.0-flash-001）
    models_to_try = [
        'gemini-2.5-flash',
        'gemini-3.5-flash',
        'gemini-2.5-flash-lite',
    ]
    response = None

    for model_name in models_to_try:
        max_retries = 3
        base_wait = 20  # 秒，503 時的等待基數

        for attempt in range(max_retries):
            try:
                print(f"Trying model: {model_name} (attempt {attempt + 1}/{max_retries})...")
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

                if "503" in error_msg or "UNAVAILABLE" in error_msg:
                    wait_sec = base_wait * (2 ** attempt)  # 指數退避: 20s, 40s, 80s
                    print(f"  ⏳ API 暫時過載 (503)。等待 {wait_sec} 秒後重試...")
                    time.sleep(wait_sec)
                elif "429" in error_msg or "Quota exceeded" in error_msg:
                    print("  ⏳ API Quota 已耗盡 (429)。等待 60 秒後重試...")
                    time.sleep(60)
                else:
                    break  # 非暫時性錯誤，直接換下一個模型

        if response:
            break

    if getattr(response, 'text', None) is None:
        print("❌ All models failed to respond. Please check API status.")
        return None

    try:
        if getattr(response, 'parsed', None):
            result_json = response.parsed
        else:
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            import re
            json_match = re.search(r'\{.*\}', clean_text, re.DOTALL)
            if json_match:
                clean_text = json_match.group(0)
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
        print(f"\n❌ Fatal error parsing JSON output: {e}")
        print("-" * 30)
        print(f"Model returned (Length: {len(response.text)}):")
        print(response.text[:1000])
        print("...")
        print(response.text[-500:] if len(response.text) > 500 else "")
        print("-" * 30)
        return None


def review_and_improve_script(script: str, client=None) -> str:
    """
    AI 編輯審稿：在 TTS 之前檢查稿件品質。
    - 確認字數在 1800–2400 字之間（對應 8–12 分鐘）
    - 移除 Markdown 格式符號（#, **, *, ---）
    - 若字數不足，要求 AI 補寫至 1800 字
    - 回傳審閱後的稿件（若無問題，回傳原稿）
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not client:
        if not api_key:
            print("⚠️ [AI Editor] 無 GEMINI_API_KEY，跳過 AI 審稿，僅做格式清理。")
            return _clean_script_formatting(script)
        client = genai.Client(api_key=api_key)

    word_count = len(script.split())
    print(f"\n📝 [AI Editor] 審稿中... 目前字數: {word_count} 字")

    # ── 先做格式清理（無論 AI 是否介入）──
    script = _clean_script_formatting(script)

    needs_expansion = word_count < 1800
    needs_trim = word_count > 2600

    if not needs_expansion and not needs_trim:
        print(f"  ✔️ [AI Editor] 字數 ({word_count}) 在合理範圍內，稿件通過審閱。")
        return script

    if needs_expansion:
        action = "EXPAND"
        instruction = (
            f"The current script is only {word_count} words, which is far too short for an 8–12 minute podcast. "
            "You MUST expand it to between 1800 and 2200 words. Add deeper analysis, expat context, and historical "
            "background to each major story. Do NOT add filler, repetition, or new topics not in the original. "
            "CRITICAL: Do NOT exceed 2200 words under any circumstances."
        )
    else:
        action = "TRIM"
        instruction = (
            f"The current script is {word_count} words, which is slightly long. "
            "Trim it to under 2400 words by cutting redundant sentences, but keep all main stories and the closing intact."
        )

    print(f"  🤖 [AI Editor] 正在 {action} 稿件...")

    editor_prompt = f"""
    You are a senior podcast editor for "The Hungarian Daily", an English-language daily news podcast.

    {instruction}

    STRICT RULES:
    1. Output ONLY the revised script text. No JSON, no markdown, no explanation.
    2. Do NOT add any Markdown formatting (no #, ##, **, *, ---).
    3. Do NOT add Hungarian vocabulary lessons or "word of the day" segments.
    4. Do NOT invent new facts, numbers, or events.
    5. Maintain the same host voice and NPR-style tone.
    6. CRITICAL: The script MUST end with the full closing CTA and "Viszlát!" sign-off. If the original script is missing this or it is cut off, you MUST restore it: add "That's all for today's Hungarian Daily. If you enjoyed this episode, please subscribe, share it with friends and colleagues in Budapest, and drop us a review wherever you listen — it really helps. I'm Ray, and I'll see you tomorrow. Viszlát!"
    7. When trimming, NEVER cut the closing CTA or sign-off — trim from the middle of news stories instead.
    8. DO NOT list or enumerate the target audience by name anywhere in the script. Remove any phrases like "our community of foreign professionals, expats, digital nomads, and international executives" — replace them with direct address to the listener ("you").

    HERE IS THE CURRENT SCRIPT:
    ---
    {script}
    ---
    """

    editor_models = ['gemini-2.5-flash', 'gemini-3.5-flash', 'gemini-2.5-flash-lite']
    revised = None
    used_model = None
    for model_name in editor_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=editor_prompt,
                config=types.GenerateContentConfig(temperature=0.4)
            )
            revised = _clean_script_formatting(response.text.strip())
            used_model = model_name
            new_word_count = len(revised.split())
            print(f"  ✔️ [AI Editor] 審稿完成 (使用 {model_name})，修訂後字數: {new_word_count} 字")
            break
        except Exception as e:
            print(f"  ⚠️ [AI Editor] {model_name} 失敗: {e}")
            time.sleep(15)

    if revised is None:
        print("  ⚠️ [AI Editor] 所有模型均失敗，回傳格式清理後的原稿。")
        return script

    # ── Second-pass trim: if expansion overshot the 2400-word target, trim it ─
    post_edit_count = len(revised.split())
    if needs_expansion and post_edit_count > 2600:
        print(f"  ⚠️ [AI Editor] 展開後字數 ({post_edit_count}) 超過上限 2600，啟動第二輪自動裁剪...")
        trim_instruction = (
            f"The current script is {post_edit_count} words, which is too long for a 10-minute podcast. "
            "Trim it to under 2400 words by removing redundant sentences and over-explained passages, "
            "but keep ALL main stories, the weather briefing, currency corner, events, and the full closing CTA intact."
        )
        trim_prompt = f"""
    You are a senior podcast editor for "The Hungarian Daily", an English-language daily news podcast.

    {trim_instruction}

    STRICT RULES:
    1. Output ONLY the revised script text. No JSON, no markdown, no explanation.
    2. Do NOT add any Markdown formatting (no #, ##, **, *, ---).
    3. NEVER cut the closing CTA or "Viszlát!" sign-off — trim from the middle of news stories instead.
    4. Maintain the same host voice and NPR-style tone.

    HERE IS THE CURRENT SCRIPT:
    ---
    {revised}
    ---
    """
        for model_name in editor_models:
            try:
                resp2 = client.models.generate_content(
                    model=model_name,
                    contents=trim_prompt,
                    config=types.GenerateContentConfig(temperature=0.3)
                )
                trimmed = _clean_script_formatting(resp2.text.strip())
                final_count = len(trimmed.split())
                print(f"  ✔️ [AI Editor] 第二輪裁剪完成 (使用 {model_name})，最終字數: {final_count} 字")
                return trimmed
            except Exception as e:
                print(f"  ⚠️ [AI Editor] 第二輪裁剪失敗 ({model_name}): {e}")
                time.sleep(10)
        print("  ⚠️ [AI Editor] 第二輪裁剪所有模型均失敗，使用第一輪結果。")

    return revised


def _clean_script_formatting(script: str) -> str:
    """
    移除 TTS 不友好的格式符號：Markdown 標題、粗體、分隔線等。
    同時移除任何意外流入播報稿的編輯評分語句。
    """
    # 移除 Markdown 標題 (# / ## / ###)
    script = re.sub(r'^#{1,6}\s+', '', script, flags=re.MULTILINE)
    # 移除粗體/斜體 (**text** 或 *text*)
    script = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', script)
    # 移除水平分隔線 (--- / *** / ___)
    script = re.sub(r'^[\-\*_]{3,}\s*$', '', script, flags=re.MULTILINE)
    # 移除評分語句（內部評分絕不應出現在播報稿中）
    # 匹配形式如："scoring a perfect 10 out of 10", "with a score of 8 out of 10",
    #             "both scoring 6 out of 10", "rated 9/10", "a 9 out of 10 story" 等
    script = re.sub(
        r'(?i)(,?\s*)'
        r'((?:both|also|each)?\s*(?:scoring|rated?|with\s+a\s+score\s+of|a\s+perfect)'
        r'\s+[a-z\s]*?\d{1,2}(?:\s*out\s*of\s*10|/10))',
        '',
        script
    )
    # 清理多餘的空行
    script = re.sub(r'\n{3,}', '\n\n', script)
    return script.strip()