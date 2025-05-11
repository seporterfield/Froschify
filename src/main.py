import logging
import os
import time
import traceback
from enum import Enum
from pathlib import Path
from typing import Callable, Tuple

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from src.config import settings
from src.edit import append_video_ffmpeg
from src.proxy import get_working_proxy
from src.youtube import dl_yt_video

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")


class VideoRequest(BaseModel):
    youtube_url: str


def make_proxy() -> dict[str, str] | None:
    proxy = (
        None
        if not settings.PROXY_CONNS or settings.PROXY_CONNS[0].strip() == ""
        else get_working_proxy(settings.PROXY_CONNS)
    )
    if proxy is None:
        return None
    _, error = dl_yt_video(url=settings.TEST_YOUTUBE_URL, proxies=proxy)
    if error:
        logger.critical(
            f"error during test youtube_dl: {error}\n{traceback.format_exc()}"
        )
        exit(1)
    return proxy


def get_yt_handler() -> Callable[
    [str, str, dict[str, str] | None, int], Tuple[str | None, Enum | None]
]:
    return dl_yt_video


def create_app() -> FastAPI:
    Path(settings.VIDEO_FOLDER).mkdir(mode=0o755, exist_ok=True)

    proxy = make_proxy()

    limiter = Limiter(key_func=get_remote_address)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
    app.add_middleware(SlowAPIMiddleware)

    # Setup templates and static files
    app.mount(
        f"/{settings.VIDEO_FOLDER}",
        StaticFiles(directory=settings.VIDEO_FOLDER),
        name=settings.VIDEO_FOLDER,
    )
    templates = Jinja2Templates(directory="templates")

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> Response:
        return templates.TemplateResponse(
            request, "index.html", context={"git_sha": "blabla123"}
        )

    @app.get("/healthz", status_code=status.HTTP_200_OK)
    async def health(request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    @app.post("/process")
    @limiter.limit("2/minute")
    async def process_video(
        request: Request,
        payload: VideoRequest,
        yt_handler: Callable[
            [str, str, dict[str, str] | None, int], Tuple[str | None, Enum | None]
        ] = Depends(get_yt_handler),
    ) -> dict[str, str]:
        youtube_url = payload.youtube_url
        downloaded_path, error = yt_handler(
            youtube_url,
            settings.VIDEO_FOLDER,
            proxy,
            settings.MAX_VIDEO_LENGTH,
        )
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error.value
            )
        if not downloaded_path:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        start = time.perf_counter()
        output_filename = append_video_ffmpeg(
            video_path=downloaded_path,
            video_toinsert_path=settings.VIDEO_TOINSERT_PATH,
            video_folder=settings.VIDEO_FOLDER,
        )
        end = time.perf_counter()
        logger.info(f"processing took {end - start}")

        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error.value
            )
        if not output_filename:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        os.remove(downloaded_path)  # Remove original downloaded video
        if os.path.exists(os.path.join(settings.VIDEO_FOLDER, output_filename)):
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
        video_path = os.path.join(os.getcwd(), settings.VIDEO_FOLDER, filename)
        logger.debug(f"{video_path = }")
        if not os.path.exists(video_path):
            logger.debug(
                f"File does not exist. Directory contents: {os.listdir(settings.VIDEO_FOLDER)}"
            )
            raise HTTPException(status_code=404, detail="Video not found")
        logger.debug(f"File exists, permissions: {oct(os.stat(video_path).st_mode)}")
        return FileResponse(path=video_path, media_type="video/mp4", filename=filename)

    return app


app = create_app()
