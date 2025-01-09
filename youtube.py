import logging
import traceback
import uuid
from enum import Enum
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from pytubefix import YouTube

logger = logging.getLogger("uvicorn.error")
MAX_VIDEO_LENGTH = 300


class YouTubeError(Enum):
    INVALID_URL = "Invalid YouTube URL format"
    UNAVAILABLE = "Video is unavailable"
    TOO_LONG = "Video exceeds maximum length of 5 minutes"
    HTTP_ERROR = "Could not access video URL"
    RATE_LIMIT = "YouTube rate limit exceeded"
    PROXY_ERROR = "Proxy connection failed"


def validate_proxy_url(proxy_url: str) -> bool:
    """Validate proxy URL format"""
    try:
        parsed = urlparse(proxy_url)
        return all([parsed.scheme, parsed.netloc])
    except Exception:
        return False


def dl_yt_video(
    url: str, output_path: str = ".", proxies: dict[str, str] | None = None
) -> Tuple[str | None, YouTubeError | None]:
    if proxies:
        logger.debug(f"Using proxies: {proxies}")
        for protocol, proxy_url in proxies.items():
            if not validate_proxy_url(proxy_url):
                logger.error(f"Invalid proxy URL for {protocol}: {proxy_url}")
                return None, YouTubeError.PROXY_ERROR

    try:
        yt = DebugYouTube(url, proxies=proxies)

        # Check if video is available (pytubefix will handle this internally)
        logger.debug(f"Video ID: {yt.video_id}")

        if yt.length() > MAX_VIDEO_LENGTH:
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


class DebugYouTube(YouTube):
    def __init__(self, url: str, proxies: Optional[Dict[str, str]] = None):
        super().__init__(url, proxies=proxies)
        self._debug_vid_info = None

    @property
    def vid_info(self) -> Dict[Any, Any]:
        """
        Override vid_info to catch and log when it's being set to None
        """
        try:
            result = super().vid_info
            if result is None:
                logger.error("vid_info is None!")
                # Log the current state
                logger.error(f"Video ID: {self.video_id}")
                logger.error(f"Client: {self.client}")
                logger.error(f"Raw vid_info: {self._vid_info}")
                # Store the last non-None value for debugging
                if self._debug_vid_info is not None:
                    logger.error(f"Last valid vid_info was: {self._debug_vid_info}")
            else:
                # Store valid response for debugging
                self._debug_vid_info = result
            return result
        except Exception as e:
            logger.error(
                f"Error in vid_info property: {str(e)}\n{traceback.format_exc()}"
            )
            raise

    @vid_info.setter
    def vid_info(self, value):
        """
        Override vid_info setter to catch when it's being set to None
        """
        if value is None:
            logger.error("Attempting to set vid_info to None!")
            logger.error(f"Current client: {self.client}")
            # Get the current stack trace
            logger.error("Stack trace:\n" + traceback.format_stack()[-2])
        self._vid_info = value

    def length(self) -> Optional[int]:
        """
        Override length to handle None values more gracefully
        """
        try:
            if self.vid_info is None:
                logger.error("Cannot get length - vid_info is None")
                return None

            video_details = self.vid_info.get("videoDetails", {})
            length_seconds = video_details.get("lengthSeconds")

            if length_seconds is None:
                logger.error("lengthSeconds is None in video_details")
                logger.error(f"Full video_details: {video_details}")
                return None

            return int(length_seconds)
        except Exception as e:
            logger.error(
                f"Error getting video length: {str(e)}\n{traceback.format_exc()}"
            )
            return None
