import json
import time
import random
import sys
import os
from datetime import datetime
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


def log(mesaj: str):
    zaman = datetime.now().strftime("%H:%M:%S")
    satir = f"[{zaman}] {mesaj}"
    print(satir, flush=True)


class InstagramBot:
    def __init__(self):
        self.cl = Client()
        self.cl.delay_range = [2, 5]
        self.claude = ClaudeProcessor()
        self.video_gen = VideoGenerator(sayfa_adi=PAGE_NAME)
        self.islenmis: set[str] = self._islenmis_yukle()

    # ---- Session ----

    def giris_yap(self):
        log("Instagram'a giris yapiliyor...")
        if SESSION_FILE.exists():
            try:
                log("Kayitli session bulundu, yukleniyor...")
                self.cl.load_settings(str(SESSION_FILE))
                self.cl.get_timeline_feed()
                log("Session gecerli, login atildi.")
                return
            except LoginRequired:
                log("Session suresi dolmus, yeniden login yapiliyor...")
            except Exception as e:
                log(f"Session hatasi: {e} — yeniden login yapiliyor...")

        log(f"Kullanici adi ile giris: {IG_USERNAME}")
        self.cl.login(IG_USERNAME, IG_PASSWORD)
        self.cl.dump_settings(str(SESSION_FILE))
        log("Login basarili, session kaydedildi.")

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
        log("DM'ler taraniyor...")
        itiraflar = []
        try:
            threads = self.cl.direct_threads(amount=50)
            log(f"{len(threads)} DM thread'i bulundu.")
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
            if itiraflar:
                log(f"{len(itiraflar)} yeni itiraf mesaji bulundu.")
            else:
                log("Yeni itiraf mesaji bulunamadi.")
        except Exception as e:
            log(f"DM tarama hatasi: {e}")
        return itiraflar

    # ---- Reels paylasimi ----

    def reels_paylas(self, video_yolu: str, caption: str) -> bool:
        log(f"Reels paylasiliyor: {Path(video_yolu).name}")
        try:
            self.cl.clip_upload(Path(video_yolu), caption=caption)
            log("Reels basariyla paylastirildi.")
            
            # Paylaşılan videoyu yerelden sil
            try:
                if os.path.exists(video_yolu):
                    os.remove(video_yolu)
                    log(f"Video paylaşıldı ve sistemden temizlendi: {Path(video_yolu).name}")
            except Exception as e:
                log(f"Dosya silinirken hata: {e}")
                
            return True
        except Exception as e:
            log(f"Reels paylasim hatasi: {e}")
            return False

    # ---- Tesekkur DM ----

    def tesekkur_dm_at(self, user_id):
        log(f"Tesekkur DM gonderiliyor (user_id={user_id})...")
        try:
            self.cl.direct_send(
                "Itirafin icin tesekkurler! Yakinda yayinlanacak. Bizi takip etmeyi unutma.",
                user_ids=[user_id],
            )
            log("Tesekkur DM gonderildi.")
        except Exception as e:
            log(f"Tesekkur DM gonderilemedi: {e}")

    def planli_paylasim_kontrol(self):
        log("Planli paylasimlar kontrol ediliyor...")
        meta = video_manager.meta_yukle()
        simdi = datetime.now()

        # "bekliyor" olan ve zamani gelmis olanlari bul
        paylasilacaklar = []
        for vid, k in meta.items():
            if k.get("durum") == "bekliyor" and k.get("planlanan_paylasim"):
                try:
                    plan_zamani = datetime.fromisoformat(k["planlanan_paylasim"])
                    if simdi >= plan_zamani:
                        paylasilacaklar.append(k)
                except Exception:
                    continue

        if not paylasilacaklar:
            log("Planlanmis paylasim bulunmadi.")
            return

        # En eski planliyi once paylas
        paylasilacaklar.sort(key=lambda x: x["planlanan_paylasim"])
        k = paylasilacaklar[0]
        vid = k["id"]

        log(f"Planli paylasim zamani gelmis: {vid}")
        video_yolu = str(OUTPUT_DIR / k["dosya"])
        if Path(video_yolu).exists():
            if self.reels_paylas(video_yolu, k["caption"]):
                video_manager.video_durum_guncelle(vid, "paylasıldı")
                log(f"Planli paylasim tamamlandi: {vid}")
        else:
            log(f"Hata: Video dosyasi bulunamadi {video_yolu}")
            # Hata varsa bekletmemek icin belki status degistirilebilir
            video_manager.video_durum_guncelle(vid, "dosya_yok")

    # ---- Ana dongu ----

    def calistir(self):
        log("=" * 50)
        log("Bot baslatiliyor...")
        log(f"Sayfa: {PAGE_NAME} | Hesap: {IG_USERNAME}")
        log("=" * 50)

        self.giris_yap()
        log("Bot hazir, dongu basliyor.")

        while True:
            # Once planlilari kontrol et
            self.planli_paylasim_kontrol()

            itiraflar = self.dm_tara()

            if not itiraflar:
                bekleme = random.randint(120, 300)
                log(f"Yeni itiraf yok. {bekleme} saniye bekleniyor...")
                time.sleep(bekleme)
                continue

            for kayit in itiraflar:
                mesaj_id = kayit["mesaj_id"]
                user_id = kayit["user_id"]
                ham_itiraf = kayit["itiraf"]

                log("-" * 40)
                log(f"Itiraf isleniyor: {ham_itiraf[:80]}...")

                try:
                    log("Claude: metin duzeltiliyor...")
                    itiraf = self.claude.duzenle(ham_itiraf)
                    log(f"Duzeltildi: {itiraf[:80]}...")

                    log("Claude: kategori belirleniyor...")
                    kategori = self.claude.kategori_belirle(itiraf)
                    log(f"Kategori: {kategori}")

                    log("Claude: caption uretiliyor...")
                    caption = self.claude.caption_uret(itiraf, kategori)
                    log(f"Caption: {caption[:60]}...")

                    gonderen = anonim_kullanici_adi()
                    log(f"Anonim gonderen: {gonderen}")

                    video_id = f"dm_{mesaj_id}"
                    video_adi = f"{video_id}.mp4"
                    video_yolu = str(OUTPUT_DIR / video_adi)
                    log(f"Video uretiliyor: {video_adi}")
                    self.video_gen.video_olustur(itiraf, gonderen, kategori, video_yolu)
                    log("Video uretildi.")

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

                    self.islenmis.add(mesaj_id)
                    self._islenmis_kaydet()
                    log("Itiraf tamamlandi.")

                except Exception as e:
                    log(f"HATA: {e}")
                    self.islenmis.add(mesaj_id)
                    self._islenmis_kaydet()

                bekleme = random.randint(120, 300)
                log(f"Sonraki itiraf icin {bekleme} saniye bekleniyor...")
                time.sleep(bekleme)
