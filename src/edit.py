import logging
import os
import subprocess
from enum import Enum

from moviepy import (  # type: ignore[import-untyped]
    VideoFileClip,
    concatenate_videoclips,
)

logger = logging.getLogger("uvicorn.error")


def append_clip(video: VideoFileClip, clip: VideoFileClip) -> VideoFileClip:
    duration = max(video.duration / 10, 1)
    if video.duration >= 1:
        first_half = video.subclipped(0, duration)
    else:
        first_half = video

    return concatenate_videoclips([first_half, clip], method="compose")


def append_video(
    video_path: str,
    video_toinsert_path: str,
    video_folder: str,
) -> str:
    logger.debug(f"Loading main video from {video_path}")
    main_video = VideoFileClip(video_path)
    logger.debug(f"Loading clip to insert from {video_toinsert_path}")
    video_toinsert = VideoFileClip(video_toinsert_path)

    output_filename = f"combined_{os.path.basename(video_path)}"
    output_path = os.path.join(video_folder, output_filename)

    logger.debug("Inserting video")
    final_video = append_clip(main_video, video_toinsert)
    logger.debug(f"Writing final video to {output_path}")
    final_video.write_videofile(
        output_path, threads=2, bitrate="5000k", audio_bitrate="128k", logger=None
    )

    logger.debug("Cleaning up resources")
    main_video.close()
    video_toinsert.close()
    final_video.close()
    logger.debug("Finished processing")
    return output_filename


def get_video_duration(video_path: str) -> float:
    """Get the duration of a video file using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            video_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return float(result.stdout.strip())


def get_video_resolution(video_path: str) -> tuple[int, int]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=s=x:p=0",
            video_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    width, height = result.stdout.strip().split("x")
    return int(width), int(height)


def append_video_ffmpeg(
    video_path: str, video_toinsert_path: str, video_folder: str
) -> str:
    width, height = get_video_resolution(video_path)

    output_filename = f"combined_{os.path.basename(video_path)}"
    output_path = os.path.abspath(os.path.join(video_folder, output_filename))
    duration = get_video_duration(video_path)

    trim = "trim=0:3," if duration >= 3 else ""
    atrim = "atrim=0:3," if duration >= 3 else ""

    scale_filter = f"scale={width}:{height}"

    ffmpeg_cmd = f"""
    ffmpeg -y -i "{video_path}" -i "{video_toinsert_path}" -filter_complex \\
    "[0:v]{trim}{scale_filter},setsar=1,setpts=PTS-STARTPTS[v0]; \\
     [0:a]{atrim}asetpts=PTS-STARTPTS[a0]; \\
     [1:v]{scale_filter},setsar=1,setpts=PTS-STARTPTS[v1]; \\
     [1:a]asetpts=PTS-STARTPTS[a1]; \\
     [v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]" \\
    -map "[outv]" -map "[outa]" -c:v libx264 -preset ultrafast -crf 23 \\
    -c:a aac -b:a 128k "{output_path}"
    """

    subprocess.run(ffmpeg_cmd, shell=True, check=True)
    return output_path
