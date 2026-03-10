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
    query = random.choice(queries) + " no copyright background music"
    
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
        'default_search': 'ytsearch1', # Sadece ilk sonucu al
        'max_filesize': 10 * 1024 * 1024, # 10MB üstünü indirme (reels için kısa müzik yeterli)
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([query])
        print(f"  [Müzik] '{vibe}' klasörüne müzik başarıyla indirildi.")
        return True
    except Exception as e:
        print(f"  [Müzik] İndirme hatası: {e}")
        return False

if __name__ == "__main__":
    # Test
    music_download("genel")
