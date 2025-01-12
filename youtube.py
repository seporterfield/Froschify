import logging
import os
import traceback
import uuid
from enum import Enum
from typing import Tuple
from urllib.parse import urlparse

import proglog
from moviepy import VideoFileClip
from pytubefix import YouTube

from edit import insert_clip_in_middle

logger = logging.getLogger("uvicorn.error")
MAX_VIDEO_LENGTH = 300


class YouTubeError(Enum):
    # dl_yt_video
    INVALID_URL = "Invalid YouTube URL format"
    UNAVAILABLE = "Video is unavailable"
    TOO_LONG = "Video exceeds maximum length of 5 minutes"
    HTTP_ERROR = "Could not access video URL"
    RATE_LIMIT = "YouTube rate limit exceeded"
    PROXY_ERROR = "Proxy connection failed"

    # insert_video_in_middle
    PROCESSING = "Video processing error"


def insert_video_in_middle(
    video_path: str, video_toinsert_path: str, video_folder: str, bitrate, audio_bitrate
) -> Tuple[str | None, YouTubeError | None]:
    try:
        # Load videos
        logger.debug(f"Loading main video from {video_path}")
        main_video = VideoFileClip(video_path)
        logger.debug(f"Loading clip to insert from {video_toinsert_path}")
        video_toinsert = VideoFileClip(video_toinsert_path)

        # Create output filename
        output_filename = f"combined_{os.path.basename(video_path)}"
        output_path = os.path.join(video_folder, output_filename)

        # Combine videos
        logger.debug("Inserting video")
        final_video = insert_clip_in_middle(main_video, video_toinsert)
        logger.debug(f"Writing final video to {output_path}")
        final_video.write_videofile(
            output_path,
            threads=2,
            bitrate=bitrate,
            audio_bitrate=audio_bitrate,
            logger=MilestoneLogger(),
        )

        # Clean up
        logger.debug("Cleaning up resources")
        main_video.close()
        video_toinsert.close()
        final_video.close()
        logger.debug("Finished processing")
        return output_filename, None

    except OSError as e:
        logger.error(
            f"Video processing error (OSError): {str(e)}\n{traceback.format_exc()}"
        )
        return None, YouTubeError.PROCESSING
    except Exception as e:
        logger.critical(
            f"Unexpected video processing error: {str(e)}\n{traceback.format_exc()}"
        )
        return None, YouTubeError.PROCESSING


def validate_proxy_url(proxy_url: str) -> bool:
    """Validate proxy URL format"""
    try:
        parsed = urlparse(proxy_url)
        return all([parsed.scheme, parsed.netloc])
    except Exception as e:
        logger.debug(f"Invalid proxy url: {proxy_url}\n{str(e)}\n{traceback.format_exc()}")
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
        yt = YouTube(url, proxies=proxies)

        # Check if video is available (pytubefix will handle this internally)
        logger.debug(f"Video ID: {yt.video_id}")

        if yt.length is None:
            logger.critical("couldn't get all video info, aborting")
            return None, YouTubeError.UNAVAILABLE
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

class MilestoneLogger(proglog.ProgressBarLogger):
    def __init__(self, milestones=(0, 25, 50, 75, 95)):
        super().__init__()
        self.milestones = sorted(milestones)
        self.next_milestone_index = 0
        
    def bars_callback(self, bar_name, attr, value, old_value, **kwargs):
        if attr != "frame_index":  # Only process frame_index updates
            return
            
        total = self.bars[bar_name]['total']
        if total == 0:
            return
            
        current_percentage = (value / total) * 100
        
        # Check if we've hit our next milestone
        while (self.next_milestone_index < len(self.milestones) and 
               current_percentage >= self.milestones[self.next_milestone_index]):
            print(f"Progress: {self.milestones[self.next_milestone_index]}%")
            self.next_milestone_index += 1
