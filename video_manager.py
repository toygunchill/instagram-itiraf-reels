"""Video metadata yoneticisi. output/videos_meta.json dosyasini yonetir."""
import json
from datetime import datetime
from config import OUTPUT_DIR

META_FILE = OUTPUT_DIR / "videos_meta.json"


def meta_yukle() -> dict:
    if META_FILE.exists():
        try:
            with open(META_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def meta_kaydet(meta: dict):
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def video_ekle(
    video_id: str,
    dosya: str,
    itiraf: str,
    kategori: str,
    caption: str,
    gonderen: str,
    planlanan_paylasim: str = None,
):
    meta = meta_yukle()
    meta[video_id] = {
        "id": video_id,
        "dosya": dosya,
        "itiraf": itiraf,
        "kategori": kategori,
        "caption": caption,
        "gonderen": gonderen,
        "durum": "bekliyor",
        "olusturulma": datetime.now().isoformat(),
        "paylasim_zamani": None,
        "planlanan_paylasim": planlanan_paylasim,
    }
    meta_kaydet(meta)


def video_durum_guncelle(video_id: str, durum: str):
    meta = meta_yukle()
    if video_id not in meta:
        return
    meta[video_id]["durum"] = durum
    if durum == "paylasıldı":
        meta[video_id]["paylasim_zamani"] = datetime.now().isoformat()
    meta_kaydet(meta)
