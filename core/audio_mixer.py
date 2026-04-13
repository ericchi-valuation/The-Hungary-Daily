import os
import shutil

def mix_podcast_audio(voice_file, bgm_file, output_file):
    """
    Mixes the voice track with a background music track.
    If bgm_file is missing or pydub fails, it gracefully falls back to just 
    using the voice track as the final output so the pipeline doesn't break.
    """
    # 1. Check if BGM exists
    if not os.path.exists(bgm_file):
        print(f"\n🎧 [Notice] {bgm_file} not found. Skipping background music mixing.")
        print(f"Fallback: copying {voice_file} to {output_file}")
        try:
            shutil.copy(voice_file, output_file)
            return True
        except Exception as e:
            print(f"❌ Error during fallback copy: {e}")
            return False
            
    print(f"\n[Mixer] Background music detected. Starting synthesis...")
    
    # 2. Try loading pydub
    try:
        from pydub import AudioSegment
    except ImportError as e:
        print(f"❌ Failed to load pydub: {e}")
        print("Fallback: using voice track without background music.")
        shutil.copy(voice_file, output_file)
        return True
        
    # 3. Try reading audio files
    try:
        voice = AudioSegment.from_file(voice_file)
        bgm = AudioSegment.from_file(bgm_file)
    except Exception as e:
        print(f"❌ Failed to read audio files: {e}")
        print("Fallback: using voice track without background music.")
        try:
            shutil.copy(voice_file, output_file)
            return True
        except:
            return False
    
    # 4. Logic: Core Mixing
    # Target length = 5s intro + voice length + 5s outro
    target_len = len(voice) + 10000 
    
    # Loop BGM if it's shorter than target
    while len(bgm) < target_len:
        bgm += bgm
    bgm = bgm[:target_len] 
    
    # Fade intro/outro
    intro = bgm[:5000].fade_out(2000)
    outro_start = 5000 + len(voice)
    outro = bgm[outro_start : outro_start + 5000]
    outro = outro.fade_in(2000).fade_out(3000)
    
    final_audio = intro + voice + outro
    
    # 5. Export
    try:
        final_audio.export(output_file, format="mp3", bitrate="192k")
        print(f"✅ Mixing complete! Final podcast saved as: {output_file}")
        
        # Backup original voice
        backup_name = voice_file.replace(".mp3", "_raw_voice_backup.mp3")
        if os.path.exists(voice_file):
            os.rename(voice_file, backup_name)
        return True
    except Exception as e:
        print(f"❌ Export error: {e}")
        # Final desperate fallback
        shutil.copy(voice_file, output_file)
        return True
