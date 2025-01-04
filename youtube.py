import re
import uuid
from pytubefix import YouTube
import requests

yt = YouTube("https://www.youtube.com/watch?v=0YEL6cB9_8s")

# Credit to https://stackoverflow.com/a/30795206
YOUTUBE_REGEX = r"(?:https?:\/\/)?(?:youtu\.be\/|(?:www\.|m\.)?youtube\.com\/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|\/))([a-zA-Z0-9_-]+)"
# Found in the http response of a youtube watch page with unavailable video
UNAVAILABLE_CONTENTSUBSTR = (
    "https://www.youtube.com/img/desktop/unavailable/unavailable_video.png"
)
MAX_VIDEO_LENGTH = 300


def is_yt_url(url: str) -> bool:
    yt_pattern = re.compile(YOUTUBE_REGEX)
    if not bool(yt_pattern.match(url)):
        return False
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    res = requests.get(url)
    if res.status_code != 200:
        return False
    if UNAVAILABLE_CONTENTSUBSTR in res.text:
        return False
    return True


def dl_yt_video(url: str, output_path: str = ".") -> str | None:
    if not is_yt_url(url):
        return None
    yt = YouTube(url)
    if yt.length > MAX_VIDEO_LENGTH:
        return None
    filename = str(uuid.uuid4()) + ".mp4"
    return yt.streams.get_lowest_resolution().download(
        output_path=output_path, filename=filename
    )
