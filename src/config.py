from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MAX_VIDEO_LENGTH: int = 300
    VIDEO_TOINSERT_PATH: str = "walterfrosch.mp4"
    VIDEO_FOLDER: str = "videos"
    BITRATE: str = "5000k"
    AUDIO_BITRATE: str = "4098k"
    VIDEO_WRITE_LOGGER: str | None = None
    PROXY_CONNS: list[str] = []
    TEST_YOUTUBE_URL: str = "https://www.youtube.com/watch?v=tPEE9ZwTmy0"

    class Config:
        env_file = "local.env"
        env_file_encoding = "utf-8"


settings = Settings()
