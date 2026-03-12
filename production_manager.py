import json
import os
import random
import sys
import io
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time

class ProductionManager:
    def __init__(self):
        self.status = "idle"
        self.queue = []
        self.processed_count = 0
        self.failed_count = 0
        self.total_count = 0
        self.logs = []
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        with self._lock:
            self.logs.append(entry)
            if len(self.logs) > 500: self.logs.pop(0)
        print(entry)

    def start_production(self, confessions, claude, video_gen, video_manager, output_dir, anon_func, tema_func):
        with self._lock:
            if self.status == "running": return False
            self.queue = confessions
            self.total_count = len(confessions)
            self.processed_count = 0
            self.failed_count = 0
            self.status = "running"
            self._stop_event.clear()
        
        thread = threading.Thread(
            target=self._run_loop,
            args=(claude, video_gen, video_manager, output_dir, anon_func, tema_func),
            daemon=True
        )
        thread.start()
        return True

    def stop_production(self):
        self._stop_event.set()
        with self._lock:
            if self.status == "running":
                self.status = "stopped"
                self.log("🛑 Üretim durduruldu.")

    def reset_production(self):
        with self._lock:
            self.status = "idle"
            self.logs = []
            self.queue = []
            self.processed_count = 0
            self.failed_count = 0
            self.total_count = 0
            self._stop_event.clear()
            self.log("♻️ Sistem sıfırlandı.")

    def get_status(self):
        with self._lock:
            return {
                "status": self.status,
                "progress": f"{self.processed_count}/{self.total_count}",
                "processed": self.processed_count,
                "failed": self.failed_count,
                "total": self.total_count,
                "logs": self.logs[-100:]
            }

    def _run_loop(self, claude, video_gen, video_manager, output_dir, anon_func, tema_func):
        self.log(f"🚀 Toplu Üretim Başladı. {self.total_count} video hemen üretilecek, paylaşımlar sıraya alınacak.")
        current_time = datetime.now()

        for i, item in enumerate(self.queue):
            if self._stop_event.is_set(): break

            try:
                raw_text = item.get("text", "")
                persona = item.get("persona", anon_func())
                theme = item.get("theme", "genel")
                admin_reply = item.get("admin_reply", "")
                
                if not raw_text: continue

                self.log(f"📦 [{i+1}/{self.total_count}] Üretim başlatılıyor...")
                
                # Paylaşım zamanını hesapla (Paylaşım sıraya alınıyor, üretim değil)
                if i > 0:
                    current_time += timedelta(seconds=random.randint(1500, 2700))
                
                if 1 <= current_time.hour < 8:
                    current_time = current_time.replace(hour=8, minute=random.randint(0, 30), second=0)
                
                plan_zamani = current_time.isoformat()
                
                # 1. AI Düzenleme
                self.log("🤖 AI metni ve caption'ı hazırlıyor...")
                itiraf = claude.duzenle(raw_text)
                kategori_meta = tema_func(theme)
                caption = claude.caption_uret(itiraf, kategori_meta)
                
                # 2. Video Üretimi (Hemen şimdi yapılıyor)
                video_id = f"json_{int(datetime.now().timestamp())}_{i}"
                video_adi = f"{video_id}.mp4"
                video_yolu = str(output_dir / video_adi)
                
                video_gen.video_olustur(itiraf, persona, theme, video_yolu, admin_reply=admin_reply, logger=self.log)
                
                # 3. Veritabanına Ekle (Paylaşım için sıraya girmiş oldu)
                video_manager.video_ekle(
                    video_id=video_id, dosya=video_adi, itiraf=itiraf,
                    kategori=kategori_meta, caption=caption, gonderen=persona,
                    planlanan_paylasim=plan_zamani, admin_reply=admin_reply
                )
                
                with self._lock: self.processed_count += 1
                self.log(f"✅ Üretim Tamam. Paylaşım sıraya alındı: {current_time.strftime('%d/%m %H:%M')}")

            except Exception as e:
                with self._lock: self.failed_count += 1
                self.log(f"❌ HATA: {str(e)}")

        with self._lock:
            if not self._stop_event.is_set():
                self.status = "completed"
                self.log("🏁 Tüm videolar üretildi ve Paylaşım Botu sırasına eklendi.")

production_manager = ProductionManager()
