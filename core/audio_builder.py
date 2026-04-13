import os
import requests
import asyncio
from dotenv import load_dotenv

load_dotenv()

def generate_audio_elevenlabs(script_text, output_file):
    """
    如果您在 .env 填寫了 ELEVENLABS_API_KEY，就會呼叫好萊塢級語音
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key or api_key == "your_elevenlabs_api_key_here":
        return False
        
    print("\n[Audio] ElevenLabs API Key detected — calling premium voice synthesis...")
    # 使用 Adam 聲音 (預設)
    url = "https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB" 
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": script_text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
    }
    
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with open(output_file, 'wb') as f:
            f.write(response.content)
        return True
    else:
        print(f"ElevenLabs 錯誤: {response.text}")
        return False

async def generate_audio_edge(script_text, output_file):
    """
    免費備案：呼叫 Microsoft Azure 提供的超逼真神經網路語音 (無字數限制)
    """
    print("\n[Audio] No ElevenLabs key — switching to free Microsoft Azure Edge TTS...")
    import edge_tts
    # 選擇一位具新聞專業感、有朝氣的男聲 (節奏微微加快 +5% 更像 Podcast)
    voice = "en-US-ChristopherNeural" 
    communicate = edge_tts.Communicate(script_text, voice, rate="+5%")
    await communicate.save(output_file)
    return True

def build_podcast_audio(script_file="script.txt", output_file="podcast.mp3"):
    if not os.path.exists(script_file):
        print(f"找不到講稿: {script_file}")
        return
        
    try:
        with open(script_file, "r", encoding="utf-8-sig") as f:
            script_text = f.read()
    except UnicodeDecodeError:
        # 若使用者在 Windows 上用一般文字編輯器存檔，且改變了編碼 (如 Big5/ANSI)
        with open(script_file, "r", encoding="mbcs") as f:
            script_text = f.read()

    # 清理講稿，避免 AI 念出舞台指示與 Markdown 符號
    import re
    script_text = re.sub(r'\[.*?\]', '', script_text)  # 移除 [Intro Music] 等
    script_text = script_text.replace('*', '')         # 移除粗體星號

    # 1. 嘗試用 ElevenLabs
    success = generate_audio_elevenlabs(script_text, output_file)
    
    # 2. Use free Edge TTS if ElevenLabs fails or has no key
    if not success:
        try:
            asyncio.run(generate_audio_edge(script_text, output_file))
            success = True
        except Exception as e:
            print(f"\n❌ Error generating Edge TTS audio: {e}")
            print("Please ensure edge-tts is installed: pip install edge-tts")
            return
            
    if success:
        print(f"\n🎧 Audio generated! Saved as: {output_file}")
        print("Put on your headphones and enjoy today's Hungary Daily Insider! Jó hallgatást! 🇭🇺")

if __name__ == "__main__":
    build_podcast_audio()
