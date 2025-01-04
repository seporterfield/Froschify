# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from moviepy import VideoFileClip
from pathlib import Path

from youtube import dl_yt_video
from edit import insert_clip_in_middle

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

VIDEO_PATH = "videos"
VIDEO_TOINSERT_PATH = "videos/walterfrosch.mp4"

app = FastAPI()

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

# Ensure video directory exists
Path("videos").mkdir(exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/process")
async def process_video(request: Request):
    print("test1")
    logger.info("test2")
    logger.error("test3")
    rootlogger = logging.getLogger()
    rootlogger.error("test4")
    form_data = await request.form()
    youtube_url = form_data.get("youtube_url")

    if not youtube_url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")

    # Download YouTube video
    downloaded_path, error = dl_yt_video(youtube_url, output_path=VIDEO_PATH)
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
        logger.error(f"Error editing video: {str(e)}")
        raise HTTPException(status_code=500)


@app.get("/download/{filename}")
async def download_video(filename: str):
    video_path = os.path.join(VIDEO_PATH, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(video_path, media_type="video/mp4", filename=filename)
