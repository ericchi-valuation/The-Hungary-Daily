import os
import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_podcast_script(news_data, social_data):
    """
    Feed raw news and social-media data to Gemini and produce a fully written
    English broadcast script for 'Hungary Daily Insider'.

    News may arrive in both English and Hungarian; Gemini handles translation
    and synthesis natively.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("\n❌ Error: No valid GEMINI_API_KEY found.")
        print("Please add  GEMINI_API_KEY=<your key>  to the .env file.")
        return None

    client = genai.Client(api_key=api_key)

    # -----------------------------------------------------------------------
    # Step 1 – Format raw data into structured text for the model
    # -----------------------------------------------------------------------
    sources_text = "【Today's Hungary News Headlines】\n"
    for source, articles in news_data.items():
        sources_text += f"\n--- Source: {source} ---\n"
        for a in articles:
            sources_text += f"Title: {a['title']}\nSummary: {a['summary']}\n"

    sources_text += "\n\n【Hungary Social Media Trending (Reddit r/hungary + r/budapest + Facebook Expats)】\n"
    for post in social_data:
        sources_text += f"Topic: {post['title']} (From {', '.join(post['topics'])})\n"

    today_str = datetime.date.today().strftime("%B %d, %Y")

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

    1. SYNTHESIS, NOT TRANSLATION:
       Do not just translate. Connect the dots. Group related stories thematically
       (e.g., "On the political front...", "In business and markets...", "Around the city...").
       Pick the most impactful 6–8 stories.

    2. EXPAT FOCUS & DEEP DIVE:
       Prioritise content most relevant to internationals:
       - EU–Hungary political tensions (Orbán government, rule-of-law disputes, EU funding battles)
       - Hungarian forint (HUF) exchange rate movements and inflation
       - Major foreign investments (BMW, Audi, CATL/Samsung SDI battery factories, tech sector)
       - Budapest real-estate, cost of living, and visa / residence permit changes
       - Budapest city life, public transport, and infrastructure news
       Provide expanded, analytical commentary on economic and political items — do not just skim them.

    3. FILTER TRASH:
       Completely ignore any remaining tabloid gossip, petty celebrity news, or irrelevant local crime 
       stories. If any slipped through the filters, drop them entirely.

    4. HUNGARIAN-LANGUAGE SOURCES:
       Some headlines will be in Hungarian (e.g., from Telex.hu, 444.hu, HVG.hu, Portfolio.hu).
       Read and understand them, then present the information naturally in English.
       Do not mention that the original source was in Hungarian.

    5. SOCIAL MEDIA SEGMENT:
       Always close the show with a fun "Trending in Budapest" segment.
       Pick 1–2 lively or quirky topics from the Reddit / Facebook Expats feed to help internationals
       understand Hungarian daily life, culture, and what locals are talking about.
       Keep it light and relatable.

    6. PRONUNCIATION SAFEGUARDS:
       Write out difficult Hungarian place names and words phonetically so a 
       generic English Text-to-Speech (TTS) engine won't mispronounce them.
       Examples:
         - Budapest   → "Boo-da-pesht"
         - Debrecen   → "Debb-ret-sen"
         - Miskolc    → "Mish-kolts"
         - Győr       → "Djur"
         - Pécs       → "Paych"
         - Orbán      → "Or-bahn"
         - forint     → "FOH-rint"
         - Telex      → "Teh-lex"

    7. TONE:
       Think "NPR Up First" meets "The Economist Podcast" meets a knowledgeable expat friend who 
       just had coffee in a Budapest café and wants to catch you up.
       Fast-paced, insightful, never condescending — and always end with a smile.

    ### SCRIPT FORMAT ###
    - Output ONLY the spoken words.
    - DO NOT output any stage directions like [Intro Music] or [Outro Music].
    - DO NOT output any Markdown formatting (**, *, ##, []). Text goes straight into a TTS engine.
    - Write in natural, conversational spoken English — short punchy sentences for news beats, 
      longer flowing sentences for analysis.
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
