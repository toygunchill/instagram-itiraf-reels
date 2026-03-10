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
    # "short" ve "instrumental" ekleyerek daha uygun sonuçlar alalım
    query = random.choice(queries) + " no copyright instrumental short"
    
    print(f"  [Müzik] '{vibe}' için YouTube'da aranıyor: {query}")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        # FFmpegExtractAudio post-processor .mp3 üretir
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': str(target_dir / '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch1',
        # Çok uzun videoları indirmemek için filtre (max 10 dk / 600 sn)
        'match_filter': yt_dlp.utils.match_filter_func("duration < 600"),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([query])
        
        # .webm.part gibi kalıntıları temizle (eğer indirme yarıda kesildiyse)
        for part_file in target_dir.glob("*.part"):
            part_file.unlink()
            
        print(f"  [Müzik] '{vibe}' klasörüne müzik hazır.")
        return True
    except Exception as e:
        print(f"  [Müzik] İndirme hatası: {e}")
        return False

if __name__ == "__main__":
    # Test
    music_download("lonely_night")
