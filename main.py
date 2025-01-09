# main.py
import logging
import os
import traceback
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from moviepy import VideoFileClip
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from edit import insert_clip_in_middle
from proxy import get_working_proxy
from youtube import dl_yt_video

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

VIDEO_PATH = "videos"
VIDEO_TOINSERT_PATH = "videos/walterfrosch.mp4"

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Setup templates and static files
Path("videos").mkdir(exist_ok=True)
app.mount("/videos", StaticFiles(directory="videos"), name="videos")
templates = Jinja2Templates(directory="templates")

# Ensure video directory exists

PROXY_CONNS = os.getenv("PROXY_CONNS", "").split(",")
PROXY_CONN = (
    None
    if not PROXY_CONNS or PROXY_CONNS[0].strip() == ""
    else get_working_proxy(PROXY_CONNS)
)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/process")
@limiter.limit("2/minute")
async def process_video(request: Request):
    form_data = await request.form()
    youtube_url = form_data.get("youtube_url")

    if not youtube_url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")

    # Download YouTube video
    proxies = None
    if PROXY_CONN:
        proxies = PROXY_CONN
    downloaded_path, error = dl_yt_video(
        youtube_url, output_path=VIDEO_PATH, proxies=proxies
    )
    if error:
        raise HTTPException(status_code=400, detail=error.value)

    try:
        # Load videos
        main_video = VideoFileClip(downloaded_path)
        video_toinsert = VideoFileClip(VIDEO_TOINSERT_PATH)

        # Create output filename
        output_filename = f"combined_{os.path.basename(downloaded_path)}"
        output_path = os.path.join(VIDEO_PATH, output_filename)

        # Combine videos
        final_video = insert_clip_in_middle(main_video, video_toinsert)
        final_video.write_videofile(output_path)

        # Clean up
        main_video.close()
        video_toinsert.close()
        final_video.close()
        os.remove(downloaded_path)  # Remove original downloaded video

        return {"filename": output_filename}

    except Exception as e:
        error_msg = str(e).lower()
        logger.critical(f"error editing video: {error_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500)


@app.get("/download/{filename}")
@limiter.limit("10/minute")
async def download_video(request: Request, filename: str):
    video_path = os.path.join(VIDEO_PATH, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(video_path, media_type="video/mp4", filename=filename)


if __name__ == "__main__":
    load_dotenv()
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info")
    uvicorn.run("main:app", host="127.0.0.1", port=port, log_level=log_level)
