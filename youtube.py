import uuid
from pytubefix import YouTube
from enum import Enum
from typing import Tuple
import logging

logger = logging.getLogger("uvicorn.error")
MAX_VIDEO_LENGTH = 300


class YouTubeError(Enum):
    INVALID_URL = "Invalid YouTube URL format"
    UNAVAILABLE = "Video is unavailable"
    TOO_LONG = "Video exceeds maximum length of 5 minutes"
    HTTP_ERROR = "Could not access video URL"
    RATE_LIMIT = "YouTube rate limit exceeded"


def dl_yt_video(
    url: str, output_path: str = ".", proxies: dict[str, str] | None = None
) -> Tuple[str | None, YouTubeError | None]:
    try:
        yt = YouTube(url, proxies=proxies)

        # Check if video is available (pytubefix will handle this internally)
        if yt.length > MAX_VIDEO_LENGTH:
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
            logger.error(f"YouTube rate limit in pytubefix: {error_msg}")
            return None, YouTubeError.RATE_LIMIT
        elif "unavailable" in error_msg or "private" in error_msg:
            logger.error(f"Video unavailable: {error_msg}")
            return None, YouTubeError.UNAVAILABLE
        else:
            logger.error(f"Error connecting to youtube with pytubefixed: {error_msg}")
            return None, YouTubeError.HTTP_ERROR
