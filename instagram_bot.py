import json
import time
import random
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import LoginRequired

from config import (
    IG_USERNAME, IG_PASSWORD, PAGE_NAME,
    SESSION_FILE, ISLENMIS_FILE, FOLLOWED_USERS_FILE, OUTPUT_DIR, anonim_kullanici_adi,
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
        self.cl.delay_range = [4, 9] 
        self.claude = ClaudeProcessor()
        self.video_gen = VideoGenerator(sayfa_adi=PAGE_NAME)
        self.islenmis: set[str] = self._islenmis_yukle()
        self.followed_users = self._followed_yukle()
        self.follow_target = "" # Takip edilecek hedef sayfa
        self.follow_queue = [] # Takip edileceklerin listesi (ID'ler)
        
        self.last_follow_time = datetime.min
        self.last_unfollow_time = datetime.min
        self.last_fetch_time = datetime.min
        
        self.next_follow_delay = random.randint(400, 700)
        self.next_unfollow_delay = random.randint(200, 400)
        self.last_human_action = datetime.now()

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

    # ---- Follower Automation ----

    def _followed_yukle(self) -> dict:
        if FOLLOWED_USERS_FILE.exists():
            try:
                with open(FOLLOWED_USERS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _followed_kaydet(self):
        with open(FOLLOWED_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.followed_users, f, ensure_ascii=False, indent=2)

    def hedef_takipcilerini_cek(self, hedef_kullanici_adi: str):
        if self.follow_queue:
            return
            
        if (datetime.now() - self.last_fetch_time).total_seconds() < 900:
            return

        log(f"'{hedef_kullanici_adi}' takipçileri taranıyor...")
        self.last_fetch_time = datetime.now()

        try:
            user_id = self.cl.user_id_from_username(hedef_kullanici_adi)
            followers = self.cl.user_followers(user_id, amount=100)
            log(f"Hedef sayfada {len(followers)} takipçi bulundu.")
            
            yeni_takip_sayisi = 0
            for f_id, f_info in followers.items():
                if str(f_id) not in self.followed_users and str(f_id) != str(self.cl.user_id):
                    self.follow_queue.append(f_id)
                    yeni_takip_sayisi += 1
            
            log(f"Kuyruğa {yeni_takip_sayisi} yeni kullanıcı eklendi. (Toplam Kuyruk: {len(self.follow_queue)})")
            
            if yeni_takip_sayisi == 0:
                log("Uyarı: Hiç yeni kullanıcı bulunamadı, tümü zaten takip edilmiş.")
                self.last_fetch_time = datetime.now() + timedelta(hours=1)
                
        except LoginRequired:
            log("Oturum süresi dolmuş veya login gerekiyor, yeniden giriş yapılıyor...")
            self.giris_yap()
            self.last_fetch_time = datetime.min
        except Exception as e:
            error_msg = str(e).lower()
            if "wait" in error_msg or "429" in error_msg:
                log("HATA: Instagram hız sınırı koydu. 20 dakika dinleniliyor...")
                self.last_fetch_time = datetime.now() + timedelta(minutes=20)
            else:
                log(f"Takipçi çekme hatası: {e}")

    def otomasyon_takip_et(self):
        if (datetime.now() - self.last_follow_time).total_seconds() < self.next_follow_delay:
            return

        if not self.follow_queue:
            if self.follow_target:
                self.hedef_takipcilerini_cek(self.follow_target)
            return

        user_id = str(self.follow_queue.pop(0))
        try:
            log(f"Kullanıcı takip ediliyor (ID: {user_id})...")
            self.cl.user_follow(user_id)
            self.followed_users[user_id] = {
                "followed_at": datetime.now().isoformat(),
                "status": "followed"
            }
            self._followed_kaydet()
            self.last_follow_time = datetime.now()
            self.next_follow_delay = random.randint(400, 700)
            log(f"Takip başarılı. Bir sonraki takip en erken {self.next_follow_delay} sn sonra.")
        except Exception as e:
            log(f"Takip hatası (ID: {user_id}): {e}")

    def otomasyon_takipten_cik(self):
        simdi = datetime.now()
        unfollow_bekleyenler = []

        for u_id, info in self.followed_users.items():
            if info.get("status") == "followed":
                f_time = datetime.fromisoformat(info["followed_at"])
                if (simdi - f_time).total_seconds() >= 24 * 3600:
                    unfollow_bekleyenler.append(u_id)

        if not unfollow_bekleyenler:
            return

        if (simdi - self.last_unfollow_time).total_seconds() < self.next_unfollow_delay:
            return

        user_id = unfollow_bekleyenler[0]
        try:
            log(f"Takipten çıkılıyor (ID: {user_id})...")
            self.cl.user_unfollow(user_id)
            self.followed_users[user_id]["status"] = "unfollowed"
            self.followed_users[user_id]["unfollowed_at"] = simdi.isoformat()
            self._followed_kaydet()
            self.last_unfollow_time = simdi
            self.next_unfollow_delay = random.randint(200, 400)
            log(f"Takipten çıkış başarılı. Bir sonraki çıkış en erken {self.next_unfollow_delay} sn sonra.")
        except Exception as e:
            log(f"Takipten çıkış hatası (ID: {user_id}): {e}")

    # ---- Anti-Bot & İnsani Simülasyon ----

    def uyku_kontrolu(self):
        saat = datetime.now().hour
        if 2 <= saat < 7:
            log("Gece uykusu vakti. Bot 07:00'ye kadar işlem yapmayacak.")
            time.sleep(3600)
            return True
        return False

    def insani_davranis_simule_et(self):
        if (datetime.now() - self.last_human_action).total_seconds() > random.randint(1800, 3600):
            log("İnsani davranış simüle ediliyor: Anasayfa güncelleniyor...")
            try:
                self.cl.get_timeline_feed()
                time.sleep(random.uniform(2.0, 5.0))
            except:
                pass
            finally:
                self.last_human_action = datetime.now()

    def hesap_istatistiklerini_guncelle(self):
        try:
            user_info = self.cl.user_info(self.cl.user_id)
            stats = {
                "follower_count": user_info.follower_count,
                "following_count": user_info.following_count,
                "updated_at": datetime.now().isoformat()
            }
            from config import BASE_DIR
            with open(BASE_DIR / "stats.json", "w", encoding="utf-8") as f:
                json.dump(stats, f)
        except:
            pass

    # ---- DM tarama ----

    def dm_tara(self) -> list[dict]:
        log("DM'ler taraniyor...")
        itiraflar = []
        try:
            threads = self.cl.direct_threads(amount=50)
            for thread in threads:
                for mesaj in thread.messages:
                    if mesaj.id in self.islenmis: continue
                    if mesaj.item_type != "text": continue
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
            log(f"DM tarama hatasi: {e}")
        return itiraflar

    # ---- Reels paylasimi ----

    def reels_paylas(self, video_yolu: str, caption: str) -> bool:
        log(f"Reels paylasiliyor: {Path(video_yolu).name}")
        try:
            self.cl.clip_upload(Path(video_yolu), caption=caption)
            log("Reels basariyla paylastirildi.")
            try:
                if os.path.exists(video_yolu):
                    os.remove(video_yolu)
                    log(f"Video paylaşıldı ve sistemden temizlendi: {Path(video_yolu).name}")
            except: pass
            return True
        except Exception as e:
            log(f"Reels paylasim hatasi: {e}")
            return False

    # ---- Tesekkur DM ----

    def tesekkur_dm_at(self, user_id):
        try:
            self.cl.direct_send(
                "Itirafin icin tesekkurler! Yakinda yayinlanacak.",
                user_ids=[user_id],
            )
        except: pass

    def planli_paylasim_kontrol(self):
        log("Planli paylasimlar kontrol ediliyor...")
        meta = video_manager.meta_yukle()
        simdi = datetime.now()
        paylasilacaklar = []
        for vid, k in meta.items():
            if k.get("durum") == "bekliyor" and k.get("planlanan_paylasim"):
                try:
                    plan_zamani = datetime.fromisoformat(k["planlanan_paylasim"])
                    if simdi >= plan_zamani: paylasilacaklar.append(k)
                except: continue

        if not paylasilacaklar: return
        paylasilacaklar.sort(key=lambda x: x["planlanan_paylasim"])
        k = paylasilacaklar[0]
        video_yolu = str(OUTPUT_DIR / k["dosya"])
        if Path(video_yolu).exists():
            if self.reels_paylas(video_yolu, k["caption"]):
                video_manager.video_durum_guncelle(k["id"], "paylasıldı")
        else:
            video_manager.video_durum_guncelle(k["id"], "dosya_yok")

    # ---- Ana dongu ----

    def calistir(self, mode="all"):
        log("=" * 50)
        log(f"Bot baslatiliyor (Mod: {mode})...")
        log(f"Sayfa: {PAGE_NAME} | Hesap: {IG_USERNAME}")
        log("=" * 50)

        self.giris_yap()
        log("Bot hazir, dongu basliyor.")

        while True:
            if self.uyku_kontrolu(): continue
            self.insani_davranis_simule_et()
            self.hesap_istatistiklerini_guncelle()

            # Modlara göre görev ayrımı
            if mode in ["share", "all"]:
                self.planli_paylasim_kontrol()

            if mode in ["follow", "all"]:
                self.otomasyon_takip_et()
                self.otomasyon_takipten_cik()

            if mode in ["dm", "all"]:
                itiraflar = self.dm_tara()
                if itiraflar:
                    for kayit in itiraflar:
                        log(f"Yeni DM itirafı isleniyor...")
                        try:
                            itiraf = self.claude.duzenle(kayit["itiraf"])
                            kategori = self.claude.kategori_belirle(itiraf)
                            caption = self.claude.caption_uret(itiraf, kategori)
                            gonderen = anonim_kullanici_adi()
                            video_id = f"dm_{kayit['mesaj_id']}"
                            video_adi = f"{video_id}.mp4"
                            video_yolu = str(OUTPUT_DIR / video_adi)
                            self.video_gen.video_olustur(itiraf, gonderen, kategori, video_yolu)
                            video_manager.video_ekle(video_id, video_adi, itiraf, kategori, caption, gonderen)
                            if self.reels_paylas(video_yolu, caption):
                                video_manager.video_durum_guncelle(video_id, "paylasıldı")
                                if kayit["user_id"]: self.tesekkur_dm_at(kayit["user_id"])
                            self.islenmis.add(kayit["mesaj_id"])
                            self._islenmis_kaydet()
                        except Exception as e:
                            log(f"DM isleme hatası: {e}")
                            self.islenmis.add(kayit["mesaj_id"])
                            self._islenmis_kaydet()
                        time.sleep(random.randint(10, 25))

            time.sleep(random.randint(30, 90))
