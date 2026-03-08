import os
import signal
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import BASE_DIR, OUTPUT_DIR, IG_USERNAME, IG_PASSWORD, PAGE_NAME, anonim_kullanici_adi, tema_donustur
import video_manager
from claude_processor import ClaudeProcessor
from video_generator import VideoGenerator
from production_manager import production_manager

# Log ve PID dosyalarını ayırıyoruz
DM_LOG_FILE = BASE_DIR / "dm_bot.log"
DM_PID_FILE = BASE_DIR / "dm_bot.pid"
FOLLOW_LOG_FILE = BASE_DIR / "follow_bot.log"
FOLLOW_PID_FILE = BASE_DIR / "follow_bot.pid"
SHARE_LOG_FILE = BASE_DIR / "share_bot.log"
SHARE_PID_FILE = BASE_DIR / "share_bot.pid"

app = FastAPI(title="Itiraf Reels Paneli")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Global processorlar
claude = ClaudeProcessor()
video_gen = VideoGenerator(sayfa_adi=PAGE_NAME)


# ---- Sayfa ----

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---- Video API ----

@app.get("/api/videos")
async def list_videos():
    meta = video_manager.meta_yukle()
    güncel_meta = {}
    
    # Dosya kontrolü yaparak listeyi temizle
    for vid, data in meta.items():
        video_yolu = OUTPUT_DIR / data["dosya"]
        if not video_yolu.exists() and data["durum"] == "bekliyor":
            # Eğer dosya yoksa ve hala bekliyor görünüyorsa (bot silmiş olabilir)
            data["durum"] = "paylasıldı" # Veya 'dosya_yok'
            video_manager.video_durum_guncelle(vid, data["durum"])
        güncel_meta[vid] = data
        
    return sorted(güncel_meta.values(), key=lambda v: v.get("olusturulma", ""), reverse=True)


@app.delete("/api/videos/{video_id}")
async def delete_video(video_id: str):
    ok = video_manager.video_sil(video_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Video bulunamadi")
    return {"status": "ok", "mesaj": "Video basariyla silindi"}


@app.post("/api/mark_shared/{video_id}")
async def mark_shared(video_id: str):
    meta = video_manager.meta_yukle()
    if video_id not in meta:
        raise HTTPException(status_code=404, detail="Video bulunamadi")
    
    # Dosyayı sil (Paylaşıldı durumunda dosya sistemden kalkmalı)
    data = meta[video_id]
    video_yolu = OUTPUT_DIR / data["dosya"]
    kapak_yolu = OUTPUT_DIR / (data["dosya"] + ".jpg")
    
    if video_yolu.exists(): video_yolu.unlink()
    if kapak_yolu.exists(): kapak_yolu.unlink()

    video_manager.video_durum_guncelle(video_id, "paylasıldı")
    return {"status": "ok", "mesaj": "Video paylasıldı olarak isaretlendi ve dosya silindi"}


@app.post("/api/generate_from_json")
async def generate_from_json(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Gecersiz JSON")

    confessions = data.get("confessions", [])
    if not confessions:
        raise HTTPException(status_code=400, detail="Itiraf listesi bos")

    success = production_manager.start_production(
        confessions, claude, video_gen, video_manager, OUTPUT_DIR, anonim_kullanici_adi, tema_donustur
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Zaten devam eden bir uretim var.")

    return {"status": "ok", "mesaj": f"{len(confessions)} itiraf uretim sirasina alindi."}


@app.get("/api/production/status")
async def production_status():
    return production_manager.get_status()


@app.post("/api/production/stop")
async def production_stop():
    production_manager.stop_production()
    return {"status": "ok"}


@app.post("/api/production/reset")
async def production_reset():
    production_manager.reset_production()
    return {"status": "ok"}


@app.post("/api/paylas/{video_id}")
async def paylas(video_id: str):
    meta = video_manager.meta_yukle()
    if video_id not in meta:
        raise HTTPException(status_code=404, detail="Video bulunamadi")

    kayit = meta[video_id]
    if kayit["durum"] == "paylasıldı":
        raise HTTPException(status_code=400, detail="Bu video zaten paylasıldı")

    video_yolu = str(OUTPUT_DIR / kayit["dosya"])
    if not Path(video_yolu).exists():
        raise HTTPException(status_code=404, detail="Video dosyasi bulunamadi")

    if not IG_USERNAME or not IG_PASSWORD:
        raise HTTPException(
            status_code=400,
            detail="IG_USERNAME veya IG_PASSWORD tanimli degil"
        )

    try:
        from instagram_bot import InstagramBot
        bot = InstagramBot()
        bot.giris_yap()
        ok = bot.reels_paylas(video_yolu, kayit["caption"])
        if ok:
            video_manager.video_durum_guncelle(video_id, "paylasıldı")
            return {"status": "ok", "mesaj": "Basariyla paylasıldı"}
        else:
            # Bot içindeki günlük limit veya başka bir False dönme durumu
            raise HTTPException(status_code=500, detail="Instagram paylaşımı reddetti veya günlük limite takıldınız.")
    except HTTPException:
        raise
    except Exception as e:
        # Hatanın gerçek içeriğini döndür (Örn: Dosya bulunamadı, Login hatası vb.)
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")


# ---- Bot API Yardimcilari ----

def _bot_calisiyor(pid_file: Path) -> bool:
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError, OSError):
        pid_file.unlink(missing_ok=True)
        return False

def _bot_durdur(pid_file: Path):
    if not _bot_calisiyor(pid_file):
        return False
    pid = int(pid_file.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        pid_file.unlink(missing_ok=True)
        return True
    except ProcessLookupError:
        pid_file.unlink(missing_ok=True)
        return True

# ---- DM Bot API ----

@app.get("/api/dm_bot/status")
async def dm_bot_status():
    return {"calisiyor": _bot_calisiyor(DM_PID_FILE)}

@app.post("/api/dm_bot/start")
async def dm_bot_start():
    if _bot_calisiyor(DM_PID_FILE):
        return {"status": "zaten_calisiyor"}
    
    log_f = open(DM_LOG_FILE, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-u", str(BASE_DIR / "main.py"), "--dm-bot"],
        stdout=log_f, stderr=log_f, cwd=str(BASE_DIR),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    DM_PID_FILE.write_text(str(proc.pid))
    return {"status": "baslatildi", "pid": proc.pid}

@app.post("/api/dm_bot/stop")
async def dm_bot_stop():
    if _bot_durdur(DM_PID_FILE):
        return {"status": "durduruldu"}
    return {"status": "zaten_durdu"}

@app.get("/api/dm_bot/logs")
async def dm_bot_logs(satirlar: int = 150):
    if not DM_LOG_FILE.exists(): return {"satirlar": []}
    with open(DM_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()[-satirlar:]
    return {"satirlar": [l.rstrip() for l in lines]}

@app.post("/api/dm_bot/logs/clear")
async def dm_bot_logs_clear():
    if DM_LOG_FILE.exists():
        DM_LOG_FILE.write_text("")
    return {"status": "ok"}

# ---- Follow Bot API ----

@app.get("/api/follow_bot/status")
async def follow_bot_status():
    return {"calisiyor": _bot_calisiyor(FOLLOW_PID_FILE)}

@app.post("/api/follow_bot/start")
async def follow_bot_start(target: str):
    if not target:
        raise HTTPException(status_code=400, detail="Hedef kullanıcı belirtilmedi")
    if _bot_calisiyor(FOLLOW_PID_FILE):
        return {"status": "zaten_calisiyor"}
    
    log_f = open(FOLLOW_LOG_FILE, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-u", str(BASE_DIR / "main.py"), "--follow-bot", target],
        stdout=log_f, stderr=log_f, cwd=str(BASE_DIR),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    FOLLOW_PID_FILE.write_text(str(proc.pid))
    return {"status": "baslatildi", "pid": proc.pid}

@app.post("/api/follow_bot/stop")
async def follow_bot_stop():
    if _bot_durdur(FOLLOW_PID_FILE):
        return {"status": "durduruldu"}
    return {"status": "zaten_durdu"}

@app.get("/api/follow_bot/logs")
async def follow_bot_logs(satirlar: int = 150):
    if not FOLLOW_LOG_FILE.exists(): return {"satirlar": []}
    with open(FOLLOW_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()[-satirlar:]
    return {"satirlar": [l.rstrip() for l in lines]}

@app.post("/api/follow_bot/logs/clear")
async def follow_bot_logs_clear():
    if FOLLOW_LOG_FILE.exists():
        FOLLOW_LOG_FILE.write_text("")
    return {"status": "ok"}

@app.get("/api/share_bot/status")
async def share_bot_status():
    return {"calisiyor": _bot_calisiyor(SHARE_PID_FILE)}

@app.post("/api/share_bot/start")
async def share_bot_start():
    if _bot_calisiyor(SHARE_PID_FILE):
        return {"status": "zaten_calisiyor"}
    
    log_f = open(SHARE_LOG_FILE, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-u", str(BASE_DIR / "main.py"), "--share-bot"],
        stdout=log_f, stderr=log_f, cwd=str(BASE_DIR),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    SHARE_PID_FILE.write_text(str(proc.pid))
    return {"status": "baslatildi", "pid": proc.pid}

@app.post("/api/share_bot/stop")
async def share_bot_stop():
    if _bot_durdur(SHARE_PID_FILE):
        return {"status": "durduruldu"}
    return {"status": "zaten_durdu"}

@app.get("/api/share_bot/logs")
async def share_bot_logs(satirlar: int = 150):
    if not SHARE_LOG_FILE.exists(): return {"satirlar": []}
    with open(SHARE_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()[-satirlar:]
    return {"satirlar": [l.rstrip() for l in lines]}

@app.post("/api/share_bot/logs/clear")
async def share_bot_logs_clear():
    if SHARE_LOG_FILE.exists():
        SHARE_LOG_FILE.write_text("")
    return {"status": "ok"}

# ---- Ortak Stats ----

@app.get("/api/follow/stats")
async def follow_stats():
    from config import FOLLOWED_USERS_FILE, BASE_DIR
    stats_file = BASE_DIR / "stats.json"

    follower_count = 0
    following_count = 0

    # Hesap bilgilerini çek (Botun güncellediği dosya)
    if stats_file.exists():
        try:
            with open(stats_file, "r") as f:
                s_data = json.load(f)
                follower_count = s_data.get("follower_count", 0)
                following_count = s_data.get("following_count", 0)
        except: pass

    if not FOLLOWED_USERS_FILE.exists():
        return {"followed": 0, "unfollowed": 0, "followers": follower_count, "following": following_count}

    try:
        with open(FOLLOWED_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        followed = sum(1 for x in data.values() if x["status"] == "followed")
        unfollowed = sum(1 for x in data.values() if x["status"] == "unfollowed")
        return {
            "followed": followed, 
            "unfollowed": unfollowed,
            "followers": follower_count,
            "following": following_count
        }
    except:
        return {"followed": 0, "unfollowed": 0, "followers": follower_count, "following": following_count}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
