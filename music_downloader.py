import yt_dlp
import os
import random
from pathlib import Path
from config import VIBE_QUERIES, MUZIK_DIR

def music_download(vibe: str):
    """Verilen vibe'a göre YouTube'dan telifsiz müzik indirir (Thread-Safe)."""
    target_dir = MUZIK_DIR / vibe
    target_dir.mkdir(parents=True, exist_ok=True)
    
    if list(target_dir.glob("*.mp3")):
        return True

    queries = VIBE_QUERIES.get(vibe, ["royalty free background music"])
    query = random.choice(queries) + " no copyright instrumental short"
    
    print(f"  [Müzik] '{vibe}' için YouTube'da aranıyor: {query}")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
        'outtmpl': str(target_dir / '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch1',
        'match_filter': yt_dlp.utils.match_filter_func("duration < 600"),
        # Thread içinde güvenli çalışan timeout ayarları
        'socket_timeout': 20,
        'retries': 1,
        'continuedl': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([query])
        
        for part_file in target_dir.glob("*.part"):
            part_file.unlink()
            
        print(f"  [Müzik] '{vibe}' klasörüne müzik hazır.")
        return True
    except Exception as e:
        print(f"  [Müzik] İndirme hatası: {e}")
        return False
