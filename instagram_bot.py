import json
import time
import random
import sys
import os
import signal
from datetime import datetime, timedelta
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import LoginRequired

from config import (
    IG_USERNAME, IG_PASSWORD, PAGE_NAME,
    SESSION_FILE, ISLENMIS_FILE, FOLLOWED_USERS_FILE, OUTPUT_DIR, anonim_kullanici_adi, BASE_DIR
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
        self.cl.delay_range = [5, 12] 
        self.claude = ClaudeProcessor()
        self.video_gen = VideoGenerator(sayfa_adi=PAGE_NAME)
        
        self.islenmis: set[str] = self._islenmis_yukle()
        self.followed_users = self._followed_yukle()
        self.follow_target = ""
        self.follow_queue = []
        
        self.last_follow_time = datetime.min
        self.last_fetch_time = datetime.min
        self.last_human_action = datetime.now()
        
        self.daily_stats = self._stats_yukle()
        self.next_follow_delay = random.randint(450, 900)
        
        self.running = True
        # Sinyal dinleyicileri
        signal.signal(signal.SIGTERM, self._sinyal_yakala)
        signal.signal(signal.SIGINT, self._sinyal_yakala)

    def _sinyal_yakala(self, signum, frame):
        log(f"Durdurma sinyali alındı. Güvenli çıkış yapılıyor...")
        self.running = False
        self.cikis_yap()
        sys.exit(0)

    # ---- Veri Yönetimi ----

    def _stats_yukle(self):
        path = BASE_DIR / "daily_stats.json"
        bugun = datetime.now().strftime("%Y-%m-%d")
        default = {"date": bugun, "follows": 0, "shares": 0}
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    if data.get("date") == bugun: return data
            except: pass
        return default

    def _stats_kaydet(self):
        with open(BASE_DIR / "daily_stats.json", "w") as f:
            json.dump(self.daily_stats, f)

    def _islenmis_yukle(self) -> set[str]:
        if ISLENMIS_FILE.exists():
            try:
                with open(ISLENMIS_FILE, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except: pass
        return set()

    def _islenmis_kaydet(self):
        with open(ISLENMIS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(self.islenmis), f, ensure_ascii=False, indent=2)

    def _followed_yukle(self) -> dict:
        if FOLLOWED_USERS_FILE.exists():
            try:
                with open(FOLLOWED_USERS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {}

    def _followed_kaydet(self):
        with open(FOLLOWED_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.followed_users, f, ensure_ascii=False, indent=2)

    # ---- Session ----

    def giris_yap(self, max_retries=3):
        log("Instagram'a güvenli giriş yapılıyor...")
        
        for attempt in range(max_retries):
            try:
                # Giriş yapmadan önce kademeli bekleme
                wait_time = (attempt * 15) + random.randint(5, 10)
                if attempt > 0:
                    log(f"Deneme {attempt+1}/{max_retries}. {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                else:
                    time.sleep(random.uniform(2, 5))

                if SESSION_FILE.exists():
                    try:
                        self.cl.load_settings(str(SESSION_FILE))
                        # Session kontrolü (Bu kısım 500 verebilir, o yüzden try içinde)
                        self.cl.get_timeline_feed() 
                        log("Mevcut oturumla devam ediliyor.")
                        return
                    except Exception as e:
                        log(f"Oturum kontrolü başarısız (Hata: {e}), temizleniyor...")
                        if SESSION_FILE.exists(): os.remove(SESSION_FILE)

                # Sıfırdan giriş
                self.cl.set_user_agent()
                log(f"Kullanıcı adı deneniyor: {IG_USERNAME}")
                if self.cl.login(IG_USERNAME, IG_PASSWORD):
                    self.cl.dump_settings(str(SESSION_FILE))
                    log("Yeni oturum açıldı ve kaydedildi.")
                    return
                
            except Exception as e:
                log(f"Giriş denemesinde hata oluştu: {e}")
                if attempt == max_retries - 1:
                    log("Maksimum giriş denemesine ulaşıldı. Bot durduruluyor.")
                    if SESSION_FILE.exists(): os.remove(SESSION_FILE)
                    raise
                
                # Eğer Instagram 500 hatası veriyorsa IP/Cihaz engeli olabilir, session temizle
                if "500" in str(e) or "Max retries exceeded" in str(e):
                    if SESSION_FILE.exists(): os.remove(SESSION_FILE)
                    log("Instagram 500 hatası döndürdü. Oturum sıfırlandı.")

    def cikis_yap(self):
        log("Instagram oturumu kapatılıyor...")
        try:
            self.cl.logout()
            if SESSION_FILE.exists():
                os.remove(SESSION_FILE)
            log("Başarıyla çıkış yapıldı.")
        except Exception as e:
            log(f"Çıkış hatası: {e}")

    # ---- Görevler ----

    def hedef_takipcilerini_cek(self, hedef_kullanici_adi: str):
        if self.follow_queue or (datetime.now() - self.last_fetch_time).total_seconds() < 3600:
            return

        log(f"'{hedef_kullanici_adi}' listesi taranıyor (Güvenli mod)...")
        self.last_fetch_time = datetime.now()
        try:
            user_id = self.cl.user_id_from_username(hedef_kullanici_adi)
            followers = self.cl.user_followers(user_id, amount=random.randint(30, 60))
            yeni = 0
            for f_id in followers.keys():
                if str(f_id) not in self.followed_users and str(f_id) != str(self.cl.user_id):
                    self.follow_queue.append(f_id)
                    yeni += 1
            log(f"Kuyruğa {yeni} organik aday eklendi.")
        except Exception as e:
            error_msg = str(e).lower()
            if "wait" in error_msg or "429" in error_msg or "<script" in error_msg:
                log("⚠️ Instagram hız sınırı/engel koydu. 1 saat beklenecek.")
                self.last_fetch_time = datetime.now() + timedelta(minutes=60)
            elif "login_required" in error_msg:
                log("Oturum düştü, yeniden giriş deneniyor...")
                self.giris_yap()
            else:
                log(f"Liste çekme hatası: {str(e)[:100]}...") # Sadece ilk 100 karakteri bas

    def otomasyon_takip_et(self):
        if self.daily_stats["follows"] >= 80: return # Günlük sınırı biraz daha aşağı çektim güvenlik için
        if (datetime.now() - self.last_follow_time).total_seconds() < self.next_follow_delay: return
        if not self.follow_queue:
            if self.follow_target: self.hedef_takipcilerini_cek(self.follow_target)
            return

        user_id = str(self.follow_queue.pop(0))
        try:
            log(f"Takip ediliyor: {user_id}")
            self.cl.user_follow(user_id)
            self.followed_users[user_id] = {"followed_at": datetime.now().isoformat(), "status": "followed"}
            self._followed_kaydet()
            self.daily_stats["follows"] += 1
            self._stats_kaydet()
            self.last_follow_time = datetime.now()
            self.next_follow_delay = random.randint(600, 1200) # Beklemeyi biraz artırdım
        except Exception as e:
            err = str(e).lower()
            if "wait" in err or "feedback_required" in err or "<script" in err:
                log("⚠️ Takip engeli algılandı. Takip botu 2 saat dinlendiriliyor.")
                self.last_follow_time = datetime.now() + timedelta(minutes=120)
            else:
                log(f"Takip hatası: {err[:100]}...")

    def insani_davranis_simule_et(self):
        if (datetime.now() - self.last_human_action).total_seconds() < random.randint(1200, 2400): return
        log("İnsani davranış simüle ediliyor...")
        try:
            aksiyon = random.choice(["timeline", "explore", "notifications"])
            if aksiyon == "timeline": self.cl.get_timeline_feed()
            elif aksiyon == "explore":
                m = self.cl.explore_medias(amount=5)
                if m: self.cl.media_like(m[0].id)
            elif aksiyon == "notifications": self.cl.get_recent_activity()
            time.sleep(random.uniform(3, 7))
        except: pass
        finally: self.last_human_action = datetime.now()

    def uyku_kontrolu(self):
        saat = datetime.now().hour
        if 2 <= saat < 7:
            log("Gece uykusu modu aktif (07:00'ye kadar).")
            time.sleep(1800)
            return True
        return False

    def hesap_istatistiklerini_guncelle(self):
        try:
            info = self.cl.user_info(self.cl.user_id)
            
            # Son 10 Reels izlenmesini çek ve ortalama hesapla
            avg_views = 0
            try:
                medias = self.cl.user_medias(self.cl.user_id, amount=10)
                reels = [m for m in medias if m.media_type == 2 and m.product_type == "clips"]
                if reels:
                    total_views = sum(m.play_count for m in reels)
                    avg_views = int(total_views / len(reels))
            except: pass

            stats = {
                "follower_count": info.follower_count,
                "following_count": info.following_count,
                "avg_reels_views": avg_views,
                "updated_at": datetime.now().isoformat()
            }
            with open(BASE_DIR / "stats.json", "w", encoding="utf-8") as f:
                json.dump(stats, f)
        except: pass

    def dm_tara(self) -> list:
        log("Gelen kutusu taranıyor...")
        itiraflar = []
        try:
            threads = self.cl.direct_threads(amount=20)
            for t in threads:
                for m in t.messages:
                    if m.id in self.islenmis or m.item_type != "text": continue
                    txt = (m.text or "").strip()
                    if txt.lower().startswith("itiraf:"):
                        itiraflar.append({"mesaj_id": m.id, "user_id": t.users[0].pk if t.users else None, "itiraf": txt[7:].strip()})
        except: pass
        return itiraflar

    def reels_paylas(self, video_yolu: str, caption: str) -> bool:
        if self.daily_stats["shares"] >= 50: return False
        log(f"Reels paylaşılıyor...")
        try:
            time.sleep(random.randint(5, 15))
            self.cl.clip_upload(Path(video_yolu), caption=caption)
            log("Paylaşım başarılı.")
            self.daily_stats["shares"] += 1
            self._stats_kaydet()
            if os.path.exists(video_yolu): os.remove(video_yolu)
            thumb = str(video_yolu) + ".jpg"
            if os.path.exists(thumb): os.remove(thumb)
            return True
        except Exception as e:
            # Hata mesajını güvenli bir şekilde metne çevir
            err_text = str(e).lower() if e is not None else ""
            
            # Eğer hata mesajı içinde 'status': 'ok' geçiyorsa başarılı say
            if "'status': 'ok'" in err_text or '"status": "ok"' in err_text:
                log("Bilgi: Bilinmeyen bir hata oluştu ama Instagram 'ok' yanıtı döndü. Başarılı sayılıyor...")
                self.daily_stats["shares"] += 1
                self._stats_kaydet()
                if os.path.exists(video_yolu): os.remove(video_yolu)
                thumb = str(video_yolu) + ".jpg"
                if os.path.exists(thumb): os.remove(thumb)
                return True
            log(f"Paylaşım hatası: {e}")
            return False

    def story_paylas(self, video_yolu: str) -> bool:
        log(f"Story paylaşılıyor...")
        try:
            self.cl.video_upload_to_story(Path(video_yolu))
            log("Story paylaşımı başarılı.")
            if os.path.exists(video_yolu): os.remove(video_yolu)
            return True
        except Exception as e:
            log(f"Story paylaşım hatası: {e}")
            return False

    def planli_paylasim_kontrol(self):
        log("Planlı görevler taranıyor...")
        meta = video_manager.meta_yukle()
        simdi = datetime.now()
        bekleyenler = [k for k in meta.values() if k.get("durum") == "bekliyor" and k.get("planlanan_paylasim")]
        
        # Zamanı gelmiş veya geçmiş olanları bul ve sırala
        gecmis_videolar = sorted(
            [k for k in bekleyenler if datetime.fromisoformat(k["planlanan_paylasim"]) <= simdi],
            key=lambda x: x["planlanan_paylasim"]
        )

        if not gecmis_videolar:
            log("Paylaşım zamanı gelmiş video yok.")
            return

        # Sadece İLK (en eski bekleyen) videoyu paylaş
        k = gecmis_videolar[0]
        video_yolu = str(OUTPUT_DIR / k["dosya"])
        
        if Path(video_yolu).exists():
            log(f"Sıradaki video paylaşılıyor: {k['dosya']}")
            if self.reels_paylas(video_yolu, k["caption"]):
                video_manager.video_durum_guncelle(k["id"], "paylasıldı")
                # Çok fazla video birikmişse araya 5-8 dk güvenlik süresi koy
                if len(gecmis_videolar) > 1:
                    log(f"Bekleyen {len(gecmis_videolar)-1} video daha var. 5-8 dk güvenlik beklemesi yapılıyor...")
                    time.sleep(random.randint(300, 480))
        else:
            log(f"Video dosyası bulunamadı, işaretleniyor: {k['dosya']}")
            video_manager.video_durum_guncelle(k["id"], "paylasıldı")

    def calistir(self, mode="all"):
        time.sleep(random.randint(1, 10))
        log(f"Bot başlatıldı (Mod: {mode})")
        self.giris_yap()
        while self.running:
            if self.uyku_kontrolu(): continue
            self.insani_davranis_simule_et()
            self.hesap_istatistiklerini_guncelle()
            if mode in ["share", "all"]: self.planli_paylasim_kontrol()
            if mode in ["follow", "all"]:
                self.otomasyon_takip_et()
            if mode in ["dm", "all"]:
                itiraflar = self.dm_tara()
                for kayit in itiraflar:
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
                            if kayit["user_id"]: self.cl.direct_send("İtirafın paylaşıldı!", user_ids=[kayit["user_id"]])
                        self.islenmis.add(kayit["mesaj_id"])
                        self._islenmis_kaydet()
                    except Exception as e: log(f"DM Hatası: {e}")
                    time.sleep(random.randint(20, 45))
            time.sleep(random.randint(60, 120))
