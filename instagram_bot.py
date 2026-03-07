import json
import time
import random
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import LoginRequired

from config import (
    IG_USERNAME, IG_PASSWORD, PAGE_NAME,
    SESSION_FILE, ISLENMIS_FILE, OUTPUT_DIR, anonim_kullanici_adi,
)
from claude_processor import ClaudeProcessor
from video_generator import VideoGenerator
import video_manager


class InstagramBot:
    def __init__(self):
        self.cl = Client()
        self.cl.delay_range = [2, 5]
        self.claude = ClaudeProcessor()
        self.video_gen = VideoGenerator(sayfa_adi=PAGE_NAME)
        self.islenmis: set[str] = self._islenmis_yukle()

    # ---- Session ----

    def giris_yap(self):
        if SESSION_FILE.exists():
            try:
                self.cl.load_settings(str(SESSION_FILE))
                self.cl.get_timeline_feed()
                print("Session yuklendi, login atildi.")
                return
            except LoginRequired:
                print("Session suresi dolmus, yeniden login yapiliyor...")
            except Exception as e:
                print(f"Session hatasi: {e}, yeniden login yapiliyor...")

        self.cl.login(IG_USERNAME, IG_PASSWORD)
        self.cl.dump_settings(str(SESSION_FILE))
        print("Login basarili, session kaydedildi.")

    # ---- Islenmis mesaj yonetimi ----

    def _islenmis_yukle(self) -> set[str]:
        if ISLENMIS_FILE.exists():
            try:
                with open(ISLENMIS_FILE, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                pass
        return set()

    def _islenmis_kaydet(self):
        with open(ISLENMIS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(self.islenmis), f, ensure_ascii=False, indent=2)

    # ---- DM tarama ----

    def dm_tara(self) -> list[dict]:
        """'itiraf: ' ile baslayan islenmemis DM'leri dondur."""
        itiraflar = []
        try:
            threads = self.cl.direct_threads(amount=50)
            for thread in threads:
                for mesaj in thread.messages:
                    if mesaj.id in self.islenmis:
                        continue
                    if mesaj.item_type != "text":
                        continue
                    metin = (mesaj.text or "").strip()
                    if metin.lower().startswith("itiraf:"):
                        icerik = metin[7:].strip()
                        if icerik:
                            itiraflar.append({
                                "mesaj_id": mesaj.id,
                                "user_id": thread.users[0].pk if thread.users else None,
                                "itiraf": icerik,
                            })
        except Exception as e:
            print(f"DM tarama hatasi: {e}")
        return itiraflar

    # ---- Reels paylasimi ----

    def reels_paylas(self, video_yolu: str, caption: str) -> bool:
        try:
            self.cl.clip_upload(Path(video_yolu), caption=caption)
            print(f"  Reels paylastirildi: {video_yolu}")
            return True
        except Exception as e:
            print(f"  Reels paylasiminda hata: {e}")
            return False

    # ---- Tesekkur DM ----

    def tesekkur_dm_at(self, user_id):
        try:
            self.cl.direct_send(
                "Itirafin icin tesekkurler! Yakinda yayinlanacak. Bizi takip etmeyi unutma.",
                user_ids=[user_id],
            )
            print(f"  Tesekkur DM gonderildi: user_id={user_id}")
        except Exception as e:
            print(f"  Tesekkur DM gonderilemedi: {e}")

    # ---- Ana dongu ----

    def calistir(self):
        print("Bot baslatiliyor...")
        self.giris_yap()

        while True:
            print("\nDM'ler taraniyor...")
            itiraflar = self.dm_tara()

            if not itiraflar:
                bekleme = random.randint(120, 300)
                print(f"Yeni itiraf bulunamadi. {bekleme}sn bekleniyor...")
                time.sleep(bekleme)
                continue

            for kayit in itiraflar:
                mesaj_id = kayit["mesaj_id"]
                user_id = kayit["user_id"]
                ham_itiraf = kayit["itiraf"]

                print(f"\nItiraf isleniyor: {ham_itiraf[:60]}...")

                try:
                    itiraf = self.claude.duzenle(ham_itiraf)
                    kategori = self.claude.kategori_belirle(itiraf)
                    caption = self.claude.caption_uret(itiraf, kategori)
                    gonderen = anonim_kullanici_adi()

                    print(f"  Kategori: {kategori} | Gonderen: {gonderen}")

                    video_id = f"dm_{mesaj_id}"
                    video_adi = f"{video_id}.mp4"
                    video_yolu = str(OUTPUT_DIR / video_adi)
                    self.video_gen.video_olustur(itiraf, gonderen, kategori, video_yolu)

                    # Web paneli icin metadata kaydet
                    video_manager.video_ekle(
                        video_id=video_id,
                        dosya=video_adi,
                        itiraf=itiraf,
                        kategori=kategori,
                        caption=caption,
                        gonderen=gonderen,
                    )

                    if self.reels_paylas(video_yolu, caption):
                        video_manager.video_durum_guncelle(video_id, "paylasıldı")
                        if user_id:
                            self.tesekkur_dm_at(user_id)
                        print(f"  Tamamlandi: {video_yolu}")

                    self.islenmis.add(mesaj_id)
                    self._islenmis_kaydet()

                except Exception as e:
                    print(f"  Hata: {e}")
                    self.islenmis.add(mesaj_id)
                    self._islenmis_kaydet()

                bekleme = random.randint(120, 300)
                print(f"  {bekleme}sn bekleniyor...")
                time.sleep(bekleme)
