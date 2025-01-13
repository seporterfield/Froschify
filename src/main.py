# main.py
import logging
import os
from pathlib import Path
from typing import Annotated

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from src.edit import insert_video_in_middle
from src.proxy import get_working_proxy
from src.youtube import dl_yt_video

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

MAX_VIDEO_LENGTH = int(os.getenv("MAX_VIDEO_LENGTH", "300"))

VIDEO_TOINSERT_PATH = os.getenv("VIDEO_TOINSERT_PATH", "walterfrosch.mp4")
VIDEO_FOLDER = os.getenv("VIDEO_PATH", "videos")
Path(VIDEO_FOLDER).mkdir(mode=0o755, exist_ok=True)

BITRATE = os.getenv("BITRATE", "5000k")
AUDIO_BITRATE = os.getenv("AUDIO_BITRATE", "4098k")

VIDEO_WRITE_LOGGER: str | None = os.getenv("VIDEO_WRITE_LOGGER", "")
VIDEO_WRITE_LOGGER = "bar" if VIDEO_WRITE_LOGGER == "bar" else None

PROXY_CONNS = os.getenv("PROXY_CONNS", "").split(",")
PROXY = (
    None
    if not PROXY_CONNS or PROXY_CONNS[0].strip() == ""
    else get_working_proxy(PROXY_CONNS)
)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
app.add_middleware(SlowAPIMiddleware)

# Setup templates and static files
app.mount(f"/{VIDEO_FOLDER}", StaticFiles(directory=VIDEO_FOLDER), name=VIDEO_FOLDER)
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> Response:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/healthz", status_code=status.HTTP_200_OK)
async def health(request: Request) -> str:
    return "OK"


@app.post("/process")
@limiter.limit("2/minute")
async def process_video(
    request: Request, youtube_url: Annotated[str, Form()]
) -> dict[str, str]:
    proxies = None
    if PROXY:
        proxies = PROXY
    downloaded_path, error = dl_yt_video(
        url=youtube_url,
        output_path=VIDEO_FOLDER,
        proxies=proxies,
        max_video_length=MAX_VIDEO_LENGTH,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.value)
    if not downloaded_path:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    output_filename, error = insert_video_in_middle(
        video_path=downloaded_path,
        video_toinsert_path=VIDEO_TOINSERT_PATH,
        video_folder=VIDEO_FOLDER,
        bitrate=BITRATE,
        audio_bitrate=AUDIO_BITRATE,
    )

    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.value)
    if not output_filename:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    os.remove(downloaded_path)  # Remove original downloaded video
    if os.path.exists(os.path.join(VIDEO_FOLDER, output_filename)):
        logger.debug(f"File {output_filename} successfully created")
    else:
        logger.error(
            f"File {output_filename} was not created. Check for errors in the pipeline."
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return {"filename": output_filename}


@app.get("/download/{filename}")
@limiter.limit("10/minute")
async def download_video(request: Request, filename: str) -> Response:
    logger.debug("Attempt seeing if video_path exists")
    video_path = os.path.join(os.getcwd(), VIDEO_FOLDER, filename)
    logger.debug(f"{video_path = }")
    if not os.path.exists(video_path):
        logger.debug(
            f"File does not exist. Directory contents: {os.listdir(VIDEO_FOLDER)}"
        )
        raise HTTPException(status_code=404, detail="Video not found")
    logger.debug(f"File exists, permissions: {oct(os.stat(video_path).st_mode)}")
    return FileResponse(path=video_path, media_type="video/mp4", filename=filename)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info")
    uvicorn.run("main:app", host="127.0.0.1", port=port, log_level=log_level)
