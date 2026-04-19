import os
import shutil

def mix_podcast_audio(voice_file, bgm_file, output_file):
    print("\n[Mixer] 🎵 準備進入混音中心 (嚴格檢查版)...")

    # 🚨 嚴格檢查 1：人聲檔是否存在且不是空檔案？
    if not os.path.exists(voice_file):
        raise FileNotFoundError(f"❌ 致命錯誤：找不到人聲音檔 '{voice_file}'！這代表前面的 TTS 語音根本沒有成功生成。")
    if os.path.getsize(voice_file) == 0:
        raise ValueError(f"❌ 致命錯誤：人聲音檔 '{voice_file}' 大小為 0 byte！TTS 伺服器可能阻擋了請求或發生異常。")

    # 🚨 嚴格檢查 2：配樂檔是否存在？
    if not os.path.exists(bgm_file):
        raise FileNotFoundError(f"❌ 致命錯誤：找不到配樂檔 '{bgm_file}'！您要求必須有混音，因此中斷程式。")

    print(f"  ✔️ 檔案物理檢查通過！開始載入混音套件...")
    
    # 2. Try loading pydub
    try:
        from pydub import AudioSegment
    except ImportError as e:
        raise ImportError(f"❌ 致命錯誤：無法載入 pydub 套件！請確定 requirements.txt 有正確安裝: {e}")
        
    # 3. Try reading audio files
    try:
        voice = AudioSegment.from_file(voice_file)
        bgm = AudioSegment.from_file(bgm_file)
    except Exception as e:
        raise Exception(f"❌ 致命錯誤：無法解析音檔格式 (可能是檔案損毀或系統缺少 ffmpeg)：{e}")
    
    print("  ✔️ 正在進行專業混音 (保留您的 5s 片頭 + 語音 + 5s 片尾邏輯)...")
    
    # 4. Logic: Core Mixing (完全保留您的優質邏輯)
    # Target length = 5s intro + voice length + 5s outro
    target_len = len(voice) + 10000 
    
    # Loop BGM if it's shorter than target
    while len(bgm) < target_len:
        bgm += bgm
    bgm = bgm[:target_len] 
    
    # 💡 小優化：將背景音樂稍微降音 (避免蓋過人聲)
    bgm = bgm - 12 
    
    # Fade intro/outro
    intro = bgm[:5000].fade_out(2000)
    outro_start = 5000 + len(voice)
    outro = bgm[outro_start : outro_start + 5000]
    outro = outro.fade_in(2000).fade_out(3000)
    
    final_audio = intro + voice + outro
    
    # 5. Export
    try:
        print("  ✔️ 正在輸出最終 MP3...")
        final_audio.export(output_file, format="mp3", bitrate="192k")
        print(f"✅ 混音大功告成！加上配樂的 Podcast 已儲存為：{output_file}")
        
        # Backup original voice
        backup_name = voice_file.replace(".mp3", "_raw_voice_backup.mp3")
        if os.path.exists(voice_file):
            os.rename(voice_file, backup_name)
        return True
    except Exception as e:
        raise Exception(f"❌ 致命錯誤：輸出 MP3 時發生錯誤：{e}")
