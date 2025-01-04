import re
import uuid
from pytubefix import YouTube
import requests
from enum import Enum
from typing import Tuple
import logging
import time

logger = logging.getLogger("uvicorn.error")

yt = YouTube("https://www.youtube.com/watch?v=0YEL6cB9_8s")

# Credit to https://stackoverflow.com/a/30795206
YOUTUBE_REGEX = r"(?:https?:\/\/)?(?:youtu\.be\/|(?:www\.|m\.)?youtube\.com\/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|\/))([a-zA-Z0-9_-]+)"
# Found in the http response of a youtube watch page with unavailable video
UNAVAILABLE_CONTENTSUBSTR = (
    "https://www.youtube.com/img/desktop/unavailable/unavailable_video.png"
)
MAX_VIDEO_LENGTH = 300


class YouTubeError(Enum):
    INVALID_URL = "Invalid YouTube URL format"
    UNAVAILABLE = "Video is unavailable"
    TOO_LONG = "Video exceeds maximum length of 5 minutes"
    HTTP_ERROR = "Could not access video URL"
    RATE_LIMIT = "YouTube rate limit exceeded"


def is_yt_url(url: str) -> Tuple[bool, YouTubeError | None]:
    yt_pattern = re.compile(YOUTUBE_REGEX)
    if not bool(yt_pattern.match(url)):
        logger.debug("Pattern is not valid youtube URL")
        return False, YouTubeError.INVALID_URL

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        res = requests.get(url, allow_redirects=True)

        if res.status_code == 429:
            # Get rate limit details
            retry_after = res.headers.get("Retry-After")
            x_ratelimit_reset = res.headers.get("X-RateLimit-Reset")
            x_quota_remaining = res.headers.get("X-Quota-Remaining")

            rate_limit_info = {
                "status_code": res.status_code,
                "retry_after": retry_after,
                "x_ratelimit_reset": x_ratelimit_reset,
                "x_quota_remaining": x_quota_remaining,
                "response_headers": dict(res.headers),
                "timestamp": time.time(),
            }

            logger.error(f"YouTube rate limit hit. Details: {rate_limit_info}")
            return False, YouTubeError.RATE_LIMIT
        if res.status_code != 200:
            logger.debug(f"GET request to youtube failed: {res.status_code}")
            return False, YouTubeError.HTTP_ERROR

        if UNAVAILABLE_CONTENTSUBSTR in res.text:
            logger.debug("Video is unavailable")
            return False, YouTubeError.UNAVAILABLE

        return True, None
    except Exception as e:
        logger.error("Error connecting to youtube with requests")
        logger.error(msg=str(e))
        return False, YouTubeError.HTTP_ERROR


def dl_yt_video(
    url: str, output_path: str = "."
) -> Tuple[str | None, YouTubeError | None]:
    is_valid, error = is_yt_url(url)
    if not is_valid:
        return None, error

    try:
        yt = YouTube(url)
        if yt.length > MAX_VIDEO_LENGTH:
            logger.debug("Video too long")
            return None, YouTubeError.TOO_LONG

        filename = str(uuid.uuid4()) + ".mp4"
        path = yt.streams.get_lowest_resolution().download(
            output_path=output_path, filename=filename
        )
        return path, None
    except Exception as e:
        logger.error("Error connecting to youtube with pytubefixed")
        logger.error(msg=str(e))
        return None, YouTubeError.UNAVAILABLE
