import yt_dlp
import os
import random
from pathlib import Path
from config import VIBE_QUERIES, MUZIK_DIR

def music_download(vibe: str):
    """Verilen vibe'a göre YouTube'dan telifsiz müzik indirir."""
    target_dir = MUZIK_DIR / vibe
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Mevcut dosyaları kontrol et (Zaten müzik varsa indirme)
    if list(target_dir.glob("*.mp3")):
        return True

    # Prompt Madde 4: Vibe -> Arama Sorguları
    queries = VIBE_QUERIES.get(vibe, ["royalty free background music"])
    query = random.choice(queries) + " no copyright instrumental short"
    
    print(f"  [Müzik] '{vibe}' için YouTube'da aranıyor: {query}")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': str(target_dir / '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch1',
        'match_filter': yt_dlp.utils.match_filter_func("duration < 600"),
        # Zaman aşımı ekle (30 saniye içinde cevap alamazsa iptal et)
        'socket_timeout': 30,
        'retries': 2,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 60 saniye içinde indirme bitmezse hata fırlat (büyük videoları önlemek için)
            import signal
            def handler(signum, frame):
                raise TimeoutError("İndirme çok uzun sürdü!")
            
            # MacOS/Linux için alarm sistemi
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(60) # 60 saniye limit
            
            try:
                ydl.download([query])
            finally:
                signal.alarm(0) # Alarmı iptal et
        
        for part_file in target_dir.glob("*.part"):
            part_file.unlink()
            
        print(f"  [Müzik] '{vibe}' klasörüne müzik hazır.")
        return True
    except Exception as e:
        print(f"  [Müzik] İndirme hatası: {e}")
        return False

if __name__ == "__main__":
    music_download("lonely_night")
