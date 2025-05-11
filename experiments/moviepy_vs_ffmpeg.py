import os
import subprocess

# Figure out whether the edit script is faster than
# doing the same thing with ffmpeg
# uv run python ./experiments/moviepy_vs_ffmpeg.py | grep "took time ="
import sys
from time import perf_counter
from typing import Callable

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.edit import append_video

VIDEO = "./shortest.mp4"


def use_moviepy() -> None:
    append_video(
        video_path=VIDEO,
        video_toinsert_path=VIDEO,
        video_folder="./videos",
    )


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


def use_ffmpeg() -> None:
    # def append_video_ffmpeg(
    #     video_path: str,
    #     video_toinsert_path: str,
    #     video_folder: str,
    # ) -> str:
    #     # Paths to your video files
    #     output_filename = f"combined_ffmpeg_{os.path.basename(video_path)}"
    #     output_path = os.path.join(video_folder, output_filename)

    #     duration = get_video_duration(video_path)

    #     # Trim first clip to 3 seconds
    #     trim = "trim=0:3," if duration >= 3 else ""
    #     atrim = "atrim=0:3," if duration >= 3 else ""
    #     ffmpeg_cmd = f"""
    #     ffmpeg -i "{video_path}" -i "{video_toinsert_path}" -filter_complex \
    #     "[0:v]{trim}setpts=PTS-STARTPTS[v0]; \
    #     [0:a]{atrim}asetpts=PTS-STARTPTS[a0]; \
    #     [1:v]setpts=PTS-STARTPTS[v1]; \
    #     [1:a]asetpts=PTS-STARTPTS[a1]; \
    #     [v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]" \
    #     -map "[outv]" -map "[outa]" \
    #     -c:v libx264 -preset ultrafast -crf 23 \
    #     -c:a aac -b:a 128k \
    #     "{output_path}"
    #     """

    #     subprocess.run(ffmpeg_cmd, shell=True, check=True)
    #     return output_path

    append_video_ffmpeg(
        video_path=VIDEO,
        video_toinsert_path=VIDEO,
        video_folder="./videos",
    )


def time_run(func: Callable[[], None], name: str | None = None) -> None:
    start = perf_counter()
    func()
    time = perf_counter() - start
    print(f"{name} took {time = }")


def main() -> None:
    time_run(func=use_moviepy, name="moviepy")
    time_run(func=use_ffmpeg, name="ffmpeg")


if __name__ == "__main__":
    main()
