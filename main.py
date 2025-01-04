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
    form_data = await request.form()
    youtube_url = form_data.get("youtube_url")

    if not youtube_url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")

    # Download YouTube video
    downloaded_path = dl_yt_video(youtube_url, output_path=VIDEO_PATH)
    if not downloaded_path:
        raise HTTPException(
            status_code=400, detail="Invalid YouTube URL or video too long"
        )

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
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
async def download_video(filename: str):
    video_path = os.path.join(VIDEO_PATH, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(video_path, media_type="video/mp4", filename=filename)
