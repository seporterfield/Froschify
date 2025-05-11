import logging
import os
import subprocess
import uuid

logger = logging.getLogger("uvicorn.error")


def get_video_duration(video_path: str) -> float:
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


def transcode_to_compatible(input_path: str, output_path: str) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-fflags",
            "+genpts",  # Generate consistent timestamps
            "-i",
            input_path,
            "-vf",
            "fps=30",  # Force constant frame rate (CFR)
            "-vsync",
            "cfr",  # CFR mode
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "23",
            "-g",
            "60",  # Force keyframe interval (2 sec at 30fps)
            "-keyint_min",
            "60",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            output_path,
        ],
        check=True,
    )


def append_video_ffmpeg(
    video_path: str, video_toinsert_path: str, video_folder: str
) -> str:
    os.makedirs(video_folder, exist_ok=True)

    basename = os.path.basename(video_path)
    output_filename = f"combined_{basename}"
    output_path = os.path.abspath(os.path.join(video_folder, output_filename))

    # Temp files
    trimmed_main = os.path.join(video_folder, f"trimmed_{uuid.uuid4()}.mp4")
    transcoded_main = os.path.join(video_folder, f"transcoded_{uuid.uuid4()}.mp4")
    transcoded_insert = os.path.join(video_folder, f"transcoded_{uuid.uuid4()}.mp4")
    concat_list_path = os.path.join(video_folder, f"concat_list_{uuid.uuid4()}.txt")

    # Get main video duration
    duration = get_video_duration(video_path)

    if duration > 3.0:
        # Trim to 3 seconds
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-t", "3", "-c", "copy", trimmed_main],
            check=True,
        )
        main_input = trimmed_main
    else:
        main_input = video_path

    # Transcode both to ensure compatibility
    transcode_to_compatible(main_input, transcoded_main)
    transcode_to_compatible(video_toinsert_path, transcoded_insert)

    # Create concat list
    with open(concat_list_path, "w") as f:
        f.write(f"file '{os.path.abspath(transcoded_main)}'\n")
        f.write(f"file '{os.path.abspath(transcoded_insert)}'\n")

    # Concatenate
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_path,
            "-c",
            "copy",
            output_path,
        ],
        check=True,
    )

    return output_filename
