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
        
        # Güvenilir Cihaz Simülasyonu
        self.cl.set_device({
            "app_version": "311.0.0.32.118",
            "android_version": 29,
            "android_release": "10",
            "dpi": "480dpi",
            "resolution": "1080x2280",
            "manufacturer": "samsung",
            "device": "SM-G973F",
            "model": "beyond1",
            "cpu": "exynos9820",
            "version_code": "543544199",
        })

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait = 30 * attempt
                    log(f"Deneme {attempt+1}. {wait}sn bekleniyor...")
                    time.sleep(wait)

                if SESSION_FILE.exists():
                    try:
                        self.cl.load_settings(str(SESSION_FILE))
                        self.cl.get_timeline_feed() 
                        log("Mevcut oturumla devam ediliyor.")
                        return
                    except:
                        if SESSION_FILE.exists(): os.remove(SESSION_FILE)

                log(f"Kullanıcı adı deneniyor: {IG_USERNAME}")
                if self.cl.login(IG_USERNAME, IG_PASSWORD):
                    self.cl.dump_settings(str(SESSION_FILE))
                    log("Yeni oturum açıldı.")
                    return
                
            except Exception as e:
                log(f"Giriş hatası: {e}")
                if SESSION_FILE.exists(): os.remove(SESSION_FILE)
                if attempt == max_retries - 1: raise

    def cikis_yap(self):
        log("Bot durduruldu (Oturum açık tutuldu).")

    # ---- Görevler ----

    def hedef_takipcilerini_cek(self, hedef_kullanici_adi: str):
        if self.follow_queue or (datetime.now() - self.last_fetch_time).total_seconds() < 3600:
            return
        log(f"'{hedef_kullanici_adi}' listesi taranıyor...")
        self.last_fetch_time = datetime.now()
        try:
            user_id = self.cl.user_id_from_username(hedef_kullanici_adi)
            followers = self.cl.user_followers(user_id, amount=random.randint(20, 40))
            yeni = 0
            for f_id in followers.keys():
                if str(f_id) not in self.followed_users:
                    self.follow_queue.append(f_id)
                    yeni += 1
            log(f"Kuyruğa {yeni} kişi eklendi.")
        except Exception as e:
            log(f"Liste hatası: {str(e)[:50]}")

    def otomasyon_takip_et(self):
        if self.daily_stats["follows"] >= 80: return 
        if (datetime.now() - self.last_follow_time).total_seconds() < self.next_follow_delay: return
        if not self.follow_queue: return

        user_id = str(self.follow_queue.pop(0))
        try:
            log(f"Takip: {user_id}")
            self.cl.user_follow(user_id)
            self.followed_users[user_id] = {"followed_at": datetime.now().isoformat(), "status": "followed"}
            self._followed_kaydet()
            self.daily_stats["follows"] += 1
            self._stats_kaydet()
            self.last_follow_time = datetime.now()
            self.next_follow_delay = random.randint(600, 1200)
        except Exception as e:
            log(f"Takip hatası: {str(e)[:50]}")

    def insani_davranis_simule_et(self):
        if (datetime.now() - self.last_human_action).total_seconds() < 1800: return
        try:
            self.cl.get_timeline_feed()
            time.sleep(random.uniform(3, 7))
        except: pass
        finally: self.last_human_action = datetime.now()

    def uyku_kontrolu(self):
        saat = datetime.now().hour
        if 1 <= saat < 8:
            time.sleep(600)
            return True
        return False

    def hesap_istatistiklerini_guncelle(self):
        try:
            info = self.cl.user_info(self.cl.user_id)
            avg_views = 0
            try:
                medias = self.cl.user_medias(self.cl.user_id, amount=5)
                reels = [m for m in medias if m.media_type == 2 and m.product_type == "clips"]
                if reels:
                    avg_views = int(sum(m.play_count for m in reels) / len(reels))
            except: pass
            stats = {"follower_count": info.follower_count, "following_count": info.following_count, "avg_reels_views": avg_views, "updated_at": datetime.now().isoformat()}
            with open(BASE_DIR / "stats.json", "w", encoding="utf-8") as f: json.dump(stats, f)
        except: pass

    def reels_paylas(self, video_yolu: str, caption: str) -> bool:
        if self.daily_stats["shares"] >= 50: return False
        
        # KRİTİK: Dosya kilidinin açılması için FFmpeg sonrası bekleme
        log("Video hazırlığı için bekleniyor (10sn)...")
        time.sleep(10)
        
        video_path = Path(video_yolu)
        thumbnail_path = video_path.with_suffix(".jpg")
        
        try:
            import subprocess
            # Kapak üretimi
            if not thumbnail_path.exists():
                subprocess.run(['ffmpeg', '-y', '-i', str(video_path.absolute()), '-ss', '00:00:01', '-vframes', '1', str(thumbnail_path.absolute())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Metadata çekimi
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=width,height', '-of', 'json', str(video_path)]
            probe_out = json.loads(subprocess.check_output(cmd).decode())
            w = int(probe_out['streams'][0]['width'])
            h = int(probe_out['streams'][0]['height'])
            dur = float(probe_out['format']['duration'])

            log(f"Yükleme başlıyor: {w}x{h}, {dur}sn")
            
            # MoviePy Analizini ve Login Hatalarını Bypass Eden Direct Upload
            self.cl.video_upload(
                video_path,
                caption=caption,
                thumbnail=thumbnail_path,
                extra_data={
                    "product_type": "clips",
                    "width": w,
                    "height": h,
                    "duration": dur,
                    "skip_extract_metadata": True 
                }
            )
            
            log("✅ Başarılı.")
            self.daily_stats["shares"] += 1
            self._stats_kaydet()
            if video_path.exists(): os.remove(video_path)
            if thumbnail_path.exists(): os.remove(thumbnail_path)
            return True
            
        except Exception as e:
            err = str(e).lower()
            if "status': 'ok'" in err or '"status": "ok"' in err:
                log("✅ Başarılı (Yanıt 'ok').")
                self.daily_stats["shares"] += 1
                self._stats_kaydet()
                if video_path.exists(): os.remove(video_path)
                if thumbnail_path.exists(): os.remove(thumbnail_path)
                return True
            log(f"❌ Hata: {e}")
            return False

    def story_paylas(self, video_yolu: str) -> bool:
        log(f"Story paylaşılıyor...")
        try:
            self.cl.video_upload_to_story(Path(video_yolu))
            log("✅ Story başarılı.")
            if os.path.exists(video_yolu): os.remove(video_yolu)
            return True
        except Exception as e:
            log(f"❌ Story hatası: {e}")
            return False

    def planli_paylasim_kontrol(self):
        log("Paylaşım sırası kontrol ediliyor...")
        meta = video_manager.meta_yukle()
        simdi = datetime.now()
        bekleyenler = sorted([k for k in meta.values() if k.get("durum") == "bekliyor" and k.get("planlanan_paylasim")], key=lambda x: x["planlanan_paylasim"])
        
        gecmis = [k for k in bekleyenler if datetime.fromisoformat(k["planlanan_paylasim"]) <= simdi]
        if not gecmis: return

        k = gecmis[0]
        video_yolu = str(OUTPUT_DIR / k["dosya"])
        if Path(video_yolu).exists():
            if self.reels_paylas(video_yolu, k["caption"]):
                video_manager.video_durum_guncelle(k["id"], "paylasıldı")
                if len(gecmis) > 1:
                    log("Güvenlik beklemesi (7 dk)...")
                    time.sleep(420)
        else:
            video_manager.video_durum_guncelle(k["id"], "paylasıldı")

    def calistir(self, mode="all"):
        log(f"Bot başlatıldı: {mode}")
        self.giris_yap()
        while self.running:
            if self.uyku_kontrolu(): continue
            self.insani_davranis_simule_et()
            self.hesap_istatistiklerini_guncelle()
            if mode in ["share", "all"]: self.planli_paylasim_kontrol()
            if mode in ["follow", "all"]: self.otomasyon_takip_et()
            time.sleep(random.randint(60, 120))
