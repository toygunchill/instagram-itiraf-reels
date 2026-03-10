import os
import random
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=True)

# Ortam degiskenleri
IG_USERNAME = os.getenv("IG_USERNAME", "")
IG_PASSWORD = os.getenv("IG_PASSWORD", "")
PAGE_NAME = os.getenv("PAGE_NAME", "gizli_itiraf_edenler")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Proje dizinleri
BASE_DIR = Path(__file__).parent
MUZIK_DIR = BASE_DIR / "muzik"
OUTPUT_DIR = BASE_DIR / "output"
SESSION_FILE = BASE_DIR / "session.json"
ISLENMIS_FILE = BASE_DIR / "islenmis.json"
FOLLOWED_USERS_FILE = BASE_DIR / "followed_users.json"

OUTPUT_DIR.mkdir(exist_ok=True)
MUZIK_DIR.mkdir(exist_ok=True)

# Video ayarlari
VIDEO_GENISLIK = 1080
VIDEO_YUKSEKLIK = 1920
VIDEO_FPS = 30
VIDEO_SURE = 15  # saniye
TOPLAM_FRAME = VIDEO_FPS * VIDEO_SURE  # 450

# Renkler (RGB)
RENKLER = {
    "arka_plan": (10, 10, 10),
    "header_bg": (18, 18, 18),
    "balon_bg": (30, 30, 30),
    "balon_kenarlik": (50, 50, 50),
    "input_bg": (22, 22, 22),
    "input_kenarlik": (55, 55, 55),
    "beyaz": (255, 255, 255),
    "gri_acik": (180, 180, 180),
    "gri_orta": (120, 120, 120),
    "gri_koyu": (70, 70, 70),
    "profil_daire": (80, 80, 80),
    "gonderi_dugme": (60, 60, 60),
    "mavi": (0, 149, 246),
    "kirmizi_nokta": (255, 80, 80),
}

# Theme -> Music Vibe Eşleşmesi (Prompt Madde 2)
THEME_VIBES = {
    "ilişki": ["romantic_tension", "lonely_night"],
    "iliski": ["romantic_tension", "lonely_night"],
    "cinsellik": ["romantic_tension"],
    "aldatma": ["guilty_feeling"],
    "yalnızlık": ["lonely_night"],
    "yalnizlik": ["lonely_night"],
    "pişmanlık": ["guilty_feeling"],
    "pismanlik": ["guilty_feeling"],
    "kıskançlık": ["romantic_tension"],
    "kiskanclik": ["romantic_tension"],
    "öfke": ["secret_confession"],
    "ofke": ["secret_confession"],
    "merak": ["secret_confession"],
    "özsaygı": ["lonely_night"],
    "ozsaygi": ["lonely_night"],
    "iş hayatı": ["secret_confession"],
    "is hayati": ["secret_confession"],
    "is": ["secret_confession"],
    "genel": ["midnight_thoughts", "lonely_night"]
}

# Fallback Vibe Havuzu (Prompt Madde 3)
FALLBACK_VIBES = ["lonely_night", "secret_confession", "romantic_tension", "guilty_feeling", "midnight_thoughts"]

# Vibe -> Arama Sorguları (Prompt Madde 4)
VIBE_QUERIES = {
    "lonely_night": ["sad lofi night", "midnight lofi", "lonely ambient"],
    "secret_confession": ["dark ambient background", "mysterious ambient"],
    "romantic_tension": ["slow romantic beat", "soft trap love instrumental"],
    "guilty_feeling": ["sad emotional piano", "dramatic piano ambient"],
    "midnight_thoughts": ["late night lofi", "deep thought ambient"]
}

# Kategori -> muzik alt klasoru (Vibe bazlı klasör yapısı için güncellendi)
KATEGORI_MUZIK = {
    "romantic_tension": "romantic_tension",
    "lonely_night": "lonely_night",
    "guilty_feeling": "guilty_feeling",
    "secret_confession": "secret_confession",
    "midnight_thoughts": "midnight_thoughts",
    "genel": "genel"
}

# Anonim kullanici adi uretici
_KELIMELER = [
    "gizli", "sessiz", "anonim", "karanlik", "golgede", "merak",
    "hayal", "simsek", "yildiz", "ay", "gunes", "bulut",
    "firtina", "deniz", "dag", "orman", "ate", "buz",
    "kelebek", "kartal", "aslan", "kurt", "tilki", "balik",
    "mor", "kirmizi", "mavi", "yesil", "sari", "siyah",
    "kalp", "ruh", "zihin", "duygu", "sir", "umut",
]

_SIFATLAR = [
    "kucuk", "buyuk", "yalniz", "sessiz", "gizli", "karanlik",
    "parlak", "soluk", "derin", "uzak", "yakin", "ozgur",
]


def anonim_kullanici_adi() -> str:
    kelime = random.choice(_KELIMELER)
    sifat = random.choice(_SIFATLAR)
    sayi = random.randint(100, 9999)
    return f"{sifat}_{kelime}_{sayi}"


# JSON theme -> dahili kategori eslemesi
TEMA_HARITASI = {
    "ilişki": "iliski", "iliski": "iliski",
    "aldatma": "iliski", "aşk": "iliski", "ask": "iliski",
    "aile": "aile",
    "iş": "is", "is": "is", "çalışma": "is", "calisma": "is",
    "arkadaşlık": "arkadaslik", "arkadaslik": "arkadaslik", "arkadaş": "arkadaslik",
    "genel": "genel",
}


def tema_donustur(tema: str) -> str:
    """JSON'daki theme/tema degerini dahili kategori koduna donustur."""
    return TEMA_HARITASI.get(tema.lower().strip(), "genel")


def muzik_sec(tema: str) -> str | None:
    """Tema'ya göre uygun Vibe seçer, gerekirse indirir ve o klasörden rastgele müzik döndürür."""
    print(f"  [Müzik] Tema analiz ediliyor: {tema}")
    # 1. Theme Analizi (Prompt Madde 1)
    tema_key = tema.lower().strip()

    # 2. Theme -> Vibe Eşleşmesi (Prompt Madde 2)
    vibe_listesi = THEME_VIBES.get(tema_key)

    # 3. Fallback (Prompt Madde 3)
    if not vibe_listesi:
        vibe = random.choice(FALLBACK_VIBES)
        print(f"  [Müzik] Tema bulunamadı, fallback vibe seçildi: {vibe}")
    else:
        vibe = random.choice(vibe_listesi)
        print(f"  [Müzik] Vibe seçildi: {vibe}")

    # Otomatik İndirme Adımı (Prompt Madde 9 - Internet Müzik İndir)
    try:
        from music_downloader import music_download
        music_download(vibe)
    except Exception as e:
        print(f"  [Müzik] İndirme hatası (atlandı): {e}")

    # Kategori klasörü
    alt_klasor = KATEGORI_MUZIK.get(vibe, "genel")
    klasor = MUZIK_DIR / alt_klasor

    # Müzik seçimi
    dosyalar = list(klasor.glob("*.mp3"))
    if not dosyalar:
        print(f"  [Müzik] '{vibe}' klasöründe müzik yok, ana klasöre bakılıyor.")
        dosyalar = list(MUZIK_DIR.glob("*.mp3"))
        
    if not dosyalar:
        print("  [Müzik] HATA: Hiç müzik dosyası bulunamadı.")
        return None
        
    secilen = str(random.choice(dosyalar))
    print(f"  [Müzik] Seçilen dosya: {Path(secilen).name}")
    return secilen
