from enum import Enum
from functools import partial
from typing import Callable, Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.main import create_app, get_yt_handler


@pytest.fixture(scope="function")
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="function")
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_smoke(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.text == "OK"


def test_landing_page(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200


def get_local_video(
    source_file: str,
    url: str,
    output_path: str = ".",
    proxies: dict[str, str] | None = None,
    max_video_length: int = -1,
) -> Tuple[str | None, Enum | None]:
    import os
    from shutil import copyfile

    dest_path = os.path.join(output_path, "test_video.mp4")
    copyfile(source_file, dest_path)
    return dest_path, None


def test_process_short_video(app: FastAPI, client: TestClient) -> None:
    def get_yt_handler_test() -> Callable[
        [str, str, dict[str, str] | None, int], Tuple[str | None, Enum | None]
    ]:
        return partial(get_local_video, "shortest.mp4")

    app.dependency_overrides[get_yt_handler] = get_yt_handler_test
    resp = client.post(
        "/process", json={"youtube_url": "https://youtube.com/watch?v=short123"}
    )
    assert resp.status_code == 200


def test_process_long_video(app: FastAPI, client: TestClient) -> None:
    def get_yt_handler_test() -> Callable[
        [str, str, dict[str, str] | None, int], Tuple[str | None, Enum | None]
    ]:
        return partial(get_local_video, "walterfrosch.mp4")

    app.dependency_overrides[get_yt_handler] = get_yt_handler_test
    resp = client.post(
        "/process", json={"youtube_url": "https://youtube.com/watch?v=long123"}
    )
    assert resp.status_code == 200


# Feedback
# - it didnt work after opening in the player
# - would be hard to share to someone on phone since it saves to files. it should save the file to "videos" on an iPhone
# also the name is combined-blahblahblah, I can't find the video
