import os
import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

import json

# Load environment variables
load_dotenv()

def score_and_sort_articles(client, news_data):
    """
    使用 Gemini 1.5 Flash 快速為匈牙利新聞評分 (1-10)。
    考量：歐盟關係、HUF 匯率、大型投資計畫與熱度加權。
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
    
    IMPORTANT: If multiple articles discuss the same major topic (e.g., a specific Orbán government decision or a major economic report), give them a "Frequency Bonus" (+1 or +2) to reflect its importance as a top headline.
    
    OUTPUT FORMAT:
    Provide only a JSON list of objects with "id" and "score", like this:
    [{{"id": 0, "score": 8}}, {{"id": 1, "score": 5}}, ...]
    
    ARTICLES:
    {articles_list_text}
    """

    try:
        print(f"正在為 {len(all_articles)} 則匈牙利新聞評分 (歐盟與匯率權重加持中)...")
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=scoring_prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
            )
        )
        scores = json.loads(response.text)
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
    """
    Feed raw news and social-media data to Gemini and produce a fully written
    English broadcast script for 'Hungary Daily Insider'.
    (Enhanced with prioritized scoring and sorting)
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("\n❌ Error: No valid GEMINI_API_KEY found.")
        print("Please add  GEMINI_API_KEY=<your key>  to the .env file.")
        return None

    client = genai.Client(api_key=api_key)

    # -----------------------------------------------------------------------
    # Step 1 – Score and prioritize news (Top 10)
    # -----------------------------------------------------------------------
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
    today_str = datetime.datetime.now(tz).strftime("%B %d, %Y")

    # -----------------------------------------------------------------------
    # Step 2 – System Prompt: the editorial soul of Hungary Daily Insider
    # -----------------------------------------------------------------------
    system_prompt = f"""
    You are an energetic, professional yet engaging podcast host for a daily English-language news show
    called "The Hungarian Daily".

    Your strict target audience is: foreign professionals, expats, digital nomads, EU citizens, and 
    international business executives living or working in Budapest, Hungary.

    IMPORTANT: You MUST start every broadcast by warmly welcoming the listener and explicitly reading 
    today's date ({today_str}).

    Your job is to read the provided daily news headlines and social media topics — which may be partly 
    in Hungarian — and synthesize everything into a cohesive, highly engaging English podcast script.

    ### EDITORIAL GUIDELINES ###
 
    1. PRIORITIZATION & SEQUENCING:
       The news items are pre-sorted by an importance score (1-10). You MUST maintain this order in your broadcast, leading with the highest-scoring stories to capture the audience's attention immediately.
       
    2. DEPTH BY IMPORTANCE:
       Devote significantly more time and analytical detail to higher-scoring stories. Low-scoring stories should be mentioned briefly as part of a news roundup.
 
    3. EXPAT FOCUS:
       Prioritise content most relevant to internationals:
       - EU–Hungary political tensions and legal disputes.
       - Hungarian forint (HUF) exchange rate and macro-economics.
       - Major foreign investments and tech sector news.
       - Residency, visa, and legal changes for expats.
       Include these topics even if their individual score is medium, but scale their length based on the relative score.
 
    4. HUNGARIAN-LANGUAGE SOURCES:
       Some headlines will be in Hungarian. Present the information naturally in English without mentioning the original language source.
 
    5. FILTER TRASH:
       Completely ignore tabloid gossip or irrelevant local crime stories.
 
    6. SOCIAL MEDIA SEGMENT:
       Always close the show with 1–2 quirky topics from the Reddit / Facebook feed to explain Hungarian daily life and culture.
 
    7. PRONUNCIATION SAFEGUARDS:
       Write out difficult Hungarian names phonetically (e.g., "Budapest" -> "Boo-da-pesht", "forint" -> "FOH-rint").
 
    8. TONE:
       Think "NPR Up First". Fast-paced, insightful, and always end with a smile.
 
    ### SCRIPT FORMAT ###
    - Output ONLY the spoken words. No stage directions ([Intro Music]). No Markdown (**).
    - Write in natural, conversational spoken English.
    - Elaborate extensively on high-scoring stories to ensure the script is sufficiently long and detailed.
    - Target length: 1800–2200 words (~10–12 minutes of spoken audio). Do not cut corners.
    """

    print("\n[AI Working] Synthesising Hungarian news with Gemini to write the broadcast script (~20–40 sec)...")

    try:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.6,
        )

        prompt_content = f"Here are today's materials. Please write the script:\n\n{sources_text}"

        # Multi-model fallback chain
        models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
        response = None

        for model_name in models_to_try:
            try:
                print(f"Trying model: {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt_content,
                    config=config
                )
                print(f"✔️  Script generated successfully with {model_name}!")
                break
            except Exception as inner_e:
                print(f"⚠️  {model_name} failed: {inner_e}")
                continue

        if not response:
            print("❌ All models failed to respond. Please check API status.")
            return None

        script = response.text

        # Save draft for human review (semi-automated safety valve)
        with open("script.txt", "w", encoding="utf-8") as f:
            f.write(script)

        print("✅ Script ready! Draft saved to script.txt")
        return script

    except Exception as e:
        print(f"\n❌ Fatal error during Gemini generation: {e}")
        return None

if __name__ == "__main__":
    print("This module is a library. Run via main.py.")
