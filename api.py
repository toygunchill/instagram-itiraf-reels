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

BOT_LOG_FILE = BASE_DIR / "bot.log"
BOT_PID_FILE = BASE_DIR / "bot.pid"

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
    return sorted(meta.values(), key=lambda v: v.get("olusturulma", ""), reverse=True)


@app.post("/api/generate_from_json")
async def generate_from_json(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Gecersiz JSON")

    confessions = data.get("confessions", [])
    if not confessions:
        raise HTTPException(status_code=400, detail="Itiraf listesi bos")

    # Arka planda uretim baslat (API'nin donmesini beklememek icin)
    # Ancak user "hepsini direkt uretip bekle" dedi, 
    # yani hepsini hemen uretecegiz. 
    # Toplu uretim zaman alacagi icin background_tasks kullanmak daha iyi.
    
    background_tasks.add_task(toplu_uretim, confessions)
    
    return {"status": "ok", "mesaj": f"{len(confessions)} itiraf uretim sirasina alindi. 30dk ara ile paylasilacak."}


def toplu_uretim(confessions: list):
    start_time = datetime.now()
    
    for i, item in enumerate(confessions):
        try:
            raw_text = item.get("text", "")
            persona = item.get("persona", anonim_kullanici_adi())
            theme = item.get("theme", "genel")
            
            if not raw_text:
                continue

            # Claude ile duzenle
            itiraf = claude.duzenle(raw_text)
            kategori = tema_donustur(theme)
            caption = claude.caption_uret(itiraf, kategori)
            
            video_id = f"json_{int(datetime.now().timestamp())}_{i}"
            video_adi = f"{video_id}.mp4"
            video_yolu = str(OUTPUT_DIR / video_adi)
            
            # 30'ar dakika ara ile planla
            plan_zamani = (start_time + timedelta(minutes=30 * i)).isoformat()
            
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
        except Exception as e:
            print(f"Toplu uretim hatasi ({i}): {e}")


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
            raise HTTPException(status_code=500, detail="Paylasim basarisiz")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Bot API ----

def _bot_calisiyor() -> bool:
    if not BOT_PID_FILE.exists():
        return False
    try:
        pid = int(BOT_PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError, OSError):
        BOT_PID_FILE.unlink(missing_ok=True)
        return False


@app.get("/api/bot/status")
async def bot_status():
    return {"calisiyor": _bot_calisiyor()}


@app.post("/api/bot/start")
async def bot_baslat():
    if _bot_calisiyor():
        return {"status": "zaten_calisiyor"}

    log_f = open(BOT_LOG_FILE, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-u", str(BASE_DIR / "main.py"), "--bot"],
        stdout=log_f,
        stderr=log_f,
        cwd=str(BASE_DIR),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    BOT_PID_FILE.write_text(str(proc.pid))
    return {"status": "baslatildi", "pid": proc.pid}


@app.post("/api/bot/stop")
async def bot_durdur():
    if not _bot_calisiyor():
        return {"status": "zaten_durdu"}

    pid = int(BOT_PID_FILE.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    BOT_PID_FILE.unlink(missing_ok=True)
    return {"status": "durduruldu"}


@app.get("/api/bot/logs")
async def bot_logs(satirlar: int = 150):
    if not BOT_LOG_FILE.exists():
        return {"satirlar": []}
    with open(BOT_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()[-satirlar:]
    return {"satirlar": [l.rstrip() for l in lines]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
