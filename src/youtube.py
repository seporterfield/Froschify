import logging
import traceback
import uuid
from enum import Enum
from typing import Tuple

from pytubefix import YouTube  # type: ignore

from src.proxy import validate_proxy_url

logger = logging.getLogger("uvicorn.error")


class YouTubeError(Enum):
    # dl_yt_video
    INVALID_URL = "Invalid YouTube URL format"
    UNAVAILABLE = "Video is unavailable"
    TOO_LONG = "Video exceeds maximum length of 5 minutes"
    HTTP_ERROR = "Could not access video URL"
    RATE_LIMIT = "YouTube rate limit exceeded"
    PROXY_ERROR = "Proxy connection failed"


def dl_yt_video(
    url: str,
    output_path: str = ".",
    proxies: dict[str, str] | None = None,
    max_video_length: int = -1,
) -> Tuple[str | None, Enum | None]:
    if proxies:
        logger.debug(f"Using proxies: {proxies}")
        for protocol, proxy_url in proxies.items():
            if not validate_proxy_url(proxy_url):
                logger.error(f"Invalid proxy URL for {protocol}: {proxy_url}")
                return None, YouTubeError.PROXY_ERROR

    try:
        yt = YouTube(url, proxies=proxies)
        logger.debug(f"Video ID: {yt.video_id}")
        try:
            yt.vid_info
        except Exception:
            logger.warning(f"Couldn't get video info for {yt.video_id}")
            raise

        if not yt.length:
            logger.critical("couldn't get all video info, abortig")
            return None, YouTubeError.UNAVAILABLE
        if yt.length > max_video_length and max_video_length != -1:
            logger.debug("Video too long")
            return None, YouTubeError.TOO_LONG

        filename = str(uuid.uuid4()) + ".mp4"
        path = yt.streams.get_lowest_resolution().download(
            output_path=output_path, filename=filename
        )
        return path, None

    except Exception as e:
        error_msg = str(e).lower()

        # Check for specific error types
        if "429" in error_msg or "too many requests" in error_msg:
            logger.critical(
                f"YouTube rate limit in pytubefix: {error_msg}\n{traceback.format_exc()}"
            )
            return None, YouTubeError.RATE_LIMIT
        elif "unavailable" in error_msg or "private" in error_msg:
            logger.error(f"Video unavailable: {error_msg}\n{traceback.format_exc()}")
            return None, YouTubeError.UNAVAILABLE
        elif "regex_search" in error_msg:
            logger.error("Invalid YouTube URL")
            return None, YouTubeError.INVALID_URL
        else:
            logger.critical(
                f"Error connecting to youtube with pytubefixed: {error_msg}\n{traceback.format_exc()}"
            )
            return None, YouTubeError.HTTP_ERROR
