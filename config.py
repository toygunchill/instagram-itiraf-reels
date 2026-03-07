import os
import random
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Ortam degiskenleri
IG_USERNAME = os.getenv("IG_USERNAME", "")
IG_PASSWORD = os.getenv("IG_PASSWORD", "")
PAGE_NAME = os.getenv("PAGE_NAME", "itiraf.sayfasi")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Proje dizinleri
BASE_DIR = Path(__file__).parent
MUZIK_DIR = BASE_DIR / "muzik"
OUTPUT_DIR = BASE_DIR / "output"
SESSION_FILE = BASE_DIR / "session.json"
ISLENMIS_FILE = BASE_DIR / "islenmis.json"

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

# Kategori -> muzik alt klasoru
KATEGORI_MUZIK = {
    "iliski": "iliski",
    "aile": "aile",
    "is": "is",
    "arkadaslik": "arkadaslik",
    "genel": "genel",
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


def muzik_sec(kategori: str) -> str | None:
    """Kategoriye gore muzik klasorunden rastgele bir .mp3 sec."""
    alt_klasor = KATEGORI_MUZIK.get(kategori, "genel")
    klasor = MUZIK_DIR / alt_klasor
    if not klasor.exists():
        klasor = MUZIK_DIR
    dosyalar = list(klasor.glob("*.mp3"))
    if not dosyalar:
        dosyalar = list(MUZIK_DIR.glob("*.mp3"))
    if not dosyalar:
        return None
    return str(random.choice(dosyalar))
