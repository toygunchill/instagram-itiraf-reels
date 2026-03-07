import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time

class ProductionManager:
    def __init__(self):
        self.status = "idle"  # idle, running, stopped, completed
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
            if len(self.logs) > 500:
                self.logs.pop(0)
        print(entry)

    def start_production(self, confessions, claude, video_gen, video_manager, output_dir, anon_func, tema_func):
        with self._lock:
            if self.status == "running":
                return False
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
                self.log("Üretim kullanıcı tarafından durduruldu.")

    def reset_production(self):
        with self._lock:
            self.status = "idle"
            self.queue = []
            self.processed_count = 0
            self.failed_count = 0
            self.total_count = 0
            self.logs = []
            self._stop_event.clear()
            self.log("Üretim sıfırlandı.")

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
        self.log(f"Toplu üretim başlatıldı. Toplam: {self.total_count}")
        # Planlama başlangıç zamanı
        current_time = datetime.now()

        for i, item in enumerate(self.queue):
            if self._stop_event.is_set():
                break

            try:
                raw_text = item.get("text", "")
                persona = item.get("persona", anon_func())
                theme = item.get("theme", "genel")
                
                if not raw_text:
                    self.log(f"[{i+1}/{self.total_count}] Boş metin atlandı.")
                    continue

                self.log(f"[{i+1}/{self.total_count}] İşleniyor: {raw_text[:30]}...")
                
                # Paylaşım Aralığı: 1 saat (3600 sn) ile 1.5 saat (5400 sn) arası rastgele ekle
                if i > 0: # İlk video hemen veya kısa bir süre sonra olabilir, diğerleri aralıklı
                    interval = random.randint(3600, 5400)
                    current_time += timedelta(seconds=interval)
                
                # Gece Koruması: 02:00 - 07:00 arasını kontrol et
                # Eğer current_time bu aralıktaysa, sabah 07:00'ye taşı
                if 2 <= current_time.hour < 7:
                    self.log(f"  - Gece koruması: {current_time.strftime('%H:%M')} saati sabah 07:00 sonrasına erteleniyor.")
                    # Günü aynı tutup saati 07:00 + rastgele dakika yapalım
                    current_time = current_time.replace(hour=7, minute=random.randint(0, 30), second=0)
                    # Eğer çoktan ertesi güne geçtiysek veya saat zaten ilerlediyse ona göre ayarlanır
                
                plan_zamani = current_time.isoformat()
                
                # Claude ile duzenle
                itiraf = claude.duzenle(raw_text)
                kategori = tema_func(theme)
                caption = claude.caption_uret(itiraf, kategori)
                
                video_id = f"json_{int(datetime.now().timestamp())}_{i}"
                video_adi = f"{video_id}.mp4"
                video_yolu = str(output_dir / video_adi)
                
                self.log(f"  - Video üretiliyor ({kategori})...")
                video_gen.video_olustur(itiraf, persona, kategori, video_yolu)
                
                video_manager.video_ekle(
                    video_id=video_id,
                    dosya=video_adi,
                    itiraf=itiraf,
                    kategori=kategori,
                    caption=caption,
                    gonderen=persona,
                    planlanan_paylasim=plan_zamani
                )
                
                with self._lock:
                    self.processed_count += 1
                self.log(f"  - Tamamlandı. Planlanan: {current_time.strftime('%d/%m %H:%M')}")

            except Exception as e:
                with self._lock:
                    self.failed_count += 1
                self.log(f"  - HATA: {str(e)}")

        with self._lock:
            if not self._stop_event.is_set():
                self.status = "completed"
                self.log("Tüm itiraflar işlendi.")

production_manager = ProductionManager()
