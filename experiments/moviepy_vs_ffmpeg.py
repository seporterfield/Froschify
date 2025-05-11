import os

# Figure out whether the edit script is faster than
# doing the same thing with ffmpeg
# uv run python ./experiments/moviepy_vs_ffmpeg.py | grep "took time ="
import sys
from time import perf_counter
from typing import Callable


def use_moviepy() -> None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from src.edit import append_video

    _, error = append_video(
        video_path="./walterfrosch.mp4",
        video_toinsert_path="./walterfrosch.mp4",
        video_folder="./videos",
        bitrate="5000k",
        audio_bitrate="4098k",
    )
    assert error is None


def get_video_duration(video_path: str) -> float:
    import subprocess

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


def use_ffmpeg() -> None:
    import subprocess

    def append_video_ffmpeg(
        video_path: str,
        video_toinsert_path: str,
        video_folder: str,
        bitrate: str,
        audio_bitrate: str,
    ) -> str:
        # Paths to your video files
        output_filename = f"combined_ffmpeg_{os.path.basename(video_path)}"
        output_path = os.path.join(video_folder, output_filename)

        duration = get_video_duration(video_path)

        # Trim first clip to 3 seconds
        trim = "trim=0:3," if duration >= 3 else ""
        atrim = "atrim=0:3," if duration >= 3 else ""
        ffmpeg_cmd = f"""
        ffmpeg -i "{video_path}" -i "{video_toinsert_path}" -filter_complex \
        "[0:v]{trim}setpts=PTS-STARTPTS[v0]; \
        [0:a]{atrim}asetpts=PTS-STARTPTS[a0]; \
        [1:v]setpts=PTS-STARTPTS[v1]; \
        [1:a]asetpts=PTS-STARTPTS[a1]; \
        [v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]" \
        -map "[outv]" -map "[outa]" -c:v libx264 -preset ultrafast -crf 23 \
        -c:a aac -b:a {audio_bitrate} "{output_path}"
        """

        subprocess.run(ffmpeg_cmd, shell=True, check=True)
        return output_path

    append_video_ffmpeg(
        video_path="./walterfrosch.mp4",
        video_toinsert_path="./walterfrosch.mp4",
        video_folder="./videos",
        bitrate="5000k",
        audio_bitrate="4098k",
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
