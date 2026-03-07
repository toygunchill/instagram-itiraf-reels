import argparse
import json
import sys
from pathlib import Path

from config import OUTPUT_DIR, anonim_kullanici_adi, PAGE_NAME, ANTHROPIC_API_KEY
import video_manager


def json_modu(json_dosyasi: str, sayfa_adi: str):
    """JSON dosyasindan toplu video uretimi."""
    from claude_processor import ClaudeProcessor
    from video_generator import VideoGenerator

    dosya = Path(json_dosyasi)
    if not dosya.exists():
        print(f"Hata: {json_dosyasi} bulunamadi.")
        sys.exit(1)

    with open(dosya, "r", encoding="utf-8") as f:
        kayitlar = json.load(f)

    if not isinstance(kayitlar, list):
        print("Hata: JSON dosyasi bir liste olmali.")
        sys.exit(1)

    if not ANTHROPIC_API_KEY:
        print("Bilgi: ANTHROPIC_API_KEY tanimli degil, Claude olmadan calisiliyor (sablon caption, temel kategori).")

    claude = ClaudeProcessor()
    video_gen = VideoGenerator(sayfa_adi=sayfa_adi)

    print(f"{len(kayitlar)} itiraf bulundu. Islem basliyor...\n")

    for i, kayit in enumerate(kayitlar, 1):
        ham_itiraf = kayit.get("itiraf", "").strip()
        if not ham_itiraf:
            print(f"[{i}/{len(kayitlar)}] Bos itiraf atlandi.")
            continue

        print(f"[{i}/{len(kayitlar)}] Isleniyor: {ham_itiraf[:60]}...")

        try:
            itiraf = claude.duzenle(ham_itiraf)
            print(f"  Duzeltildi: {itiraf[:60]}...")

            kategori = kayit.get("kategori", "").strip().lower()
            if kategori not in {"iliski", "aile", "is", "arkadaslik", "genel"} or not kategori:
                kategori = claude.kategori_belirle(itiraf)
            print(f"  Kategori: {kategori}")

            caption = claude.caption_uret(itiraf, kategori)
            gonderen = anonim_kullanici_adi()
            print(f"  Gonderen: {gonderen}")

            video_id = f"itiraf_{i:03d}"
            video_adi = f"{video_id}.mp4"
            video_yolu = str(OUTPUT_DIR / video_adi)
            video_gen.video_olustur(itiraf, gonderen, kategori, video_yolu)

            # Caption dosyasi (eski uyumluluk icin)
            caption_yolu = str(OUTPUT_DIR / f"{video_id}_caption.txt")
            with open(caption_yolu, "w", encoding="utf-8") as f:
                f.write(caption)

            # Web paneli icin metadata kaydet
            video_manager.video_ekle(
                video_id=video_id,
                dosya=video_adi,
                itiraf=itiraf,
                kategori=kategori,
                caption=caption,
                gonderen=gonderen,
            )

            print(f"  Tamamlandi: {video_yolu}\n")

        except Exception as e:
            print(f"  Hata: {e}\n")

    print("Tum itiraflar islendi.")


def bot_modu():
    """Instagram DM otomasyon modu."""
    import os
    from config import IG_USERNAME, IG_PASSWORD
    if not IG_USERNAME or not IG_PASSWORD:
        print("Hata: IG_USERNAME veya IG_PASSWORD tanimli degil. .env dosyasini kontrol edin.")
        sys.exit(1)
    if not ANTHROPIC_API_KEY:
        print("Bilgi: ANTHROPIC_API_KEY tanimli degil, Claude olmadan calisiliyor.")

    from instagram_bot import InstagramBot
    bot = InstagramBot()
    
    # Get follow target from environment
    follow_target = os.getenv("FOLLOW_TARGET", "")
    if follow_target:
        bot.follow_target = follow_target
        print(f"Takip otomasyonu hedefi: {follow_target}")
    
    bot.calistir()


def main():
    parser = argparse.ArgumentParser(
        description="Instagram Itiraf Reels Otomasyonu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Kullanim ornekleri:
  python main.py --json data.json --page itiraf.sayfasi
  python main.py --bot
  python api.py   (web panelini baslat)
        """,
    )
    parser.add_argument("--json", metavar="DOSYA", help="JSON dosyasindan toplu video uret")
    parser.add_argument("--page", metavar="SAYFA", default=PAGE_NAME, help="Instagram sayfa adi")
    parser.add_argument("--bot", action="store_true", help="DM otomasyon modunu baslat")

    args = parser.parse_args()

    if args.json:
        json_modu(args.json, args.page)
    elif args.bot:
        bot_modu()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
