import logging
import os
import traceback
from enum import Enum
from typing import Any, Tuple

import proglog  # type: ignore
from moviepy import VideoFileClip, concatenate_videoclips  # type: ignore
from proglog import ProgressLogger

logger = logging.getLogger("uvicorn.error")


class EditError(Enum):
    PROCESSING = "Video processing error"


def append_clip(video: VideoFileClip, clip: VideoFileClip) -> VideoFileClip:
    duration = max(video.duration / 10, 1)
    first_half = video.subclipped(0, duration)

    return concatenate_videoclips([first_half, clip], method="compose")


def append_video(
    video_path: str,
    video_toinsert_path: str,
    video_folder: str,
    bitrate: str,
    audio_bitrate: str,
    video_write_logger: str | None = None,
) -> Tuple[str | None, Enum | None]:
    try:
        # Load videos
        # Just use ffmpeg! No moviepy
        # Maybe fully inmem https://github.com/kkroening/ffmpeg-python/issues/500
        logger.debug(f"Loading main video from {video_path}")
        main_video = VideoFileClip(video_path)
        logger.debug(f"Loading clip to insert from {video_toinsert_path}")
        video_toinsert = VideoFileClip(video_toinsert_path)

        # Instead, we should split video and audio tracks

        # Then edit video and audio separately (insert clip in middle)
        # Multithreaded

        # And splice video and audio back together

        # Create output filename
        output_filename = f"combined_{os.path.basename(video_path)}"
        output_path = os.path.join(video_folder, output_filename)

        # Combine videos
        logger.debug("Inserting video")
        final_video = append_clip(main_video, video_toinsert)
        logger.debug(f"Writing final video to {output_path}")
        ffmpeg_logger: ProgressLogger | str | None = None
        if video_write_logger == "milestone":
            ffmpeg_logger = MilestoneLogger()
        if video_write_logger == "bar":
            ffmpeg_logger = "bar"
        final_video.write_videofile(
            output_path,
            threads=2,
            bitrate=bitrate,
            audio_bitrate=audio_bitrate,
            logger=ffmpeg_logger,
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
        return None, EditError.PROCESSING
    except Exception as e:
        logger.critical(
            f"Unexpected video processing error: {str(e)}\n{traceback.format_exc()}"
        )
        return None, EditError.PROCESSING


class MilestoneLogger(proglog.ProgressBarLogger):  # type: ignore
    def __init__(self, milestones: list[int] = [0, 25, 50, 75, 95]):
        super().__init__()
        self.milestones = sorted(milestones)
        self.next_milestone_index = 0

    def bars_callback(
        self,
        bar_name: Any,
        attr: Any,
        value: Any,
        old_value: Any,
        **kwargs: dict[str, Any],
    ) -> None:
        total = self.bars[bar_name]["total"]
        if total == 0:
            return
        if value == 0:
            self.next_milestone_index = 0

        current_percentage = (value / total) * 100
        # Check if we've hit our next milestone
        if (
            self.next_milestone_index < len(self.milestones)
            and current_percentage >= self.milestones[self.next_milestone_index]
        ):
            logger.debug(
                f"Progress: {self.milestones[self.next_milestone_index]}% -- {bar_name}"
            )
            self.next_milestone_index += 1
