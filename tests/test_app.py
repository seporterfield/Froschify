from enum import Enum
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
    url: str,
    output_path: str = ".",
    proxies: dict[str, str] | None = None,
    max_video_length: int = -1,
) -> Tuple[str | None, Enum | None]:
    import os
    from shutil import copyfile

    source_file = "shortest.mp4"
    dest_path = os.path.join(output_path, "test_video.mp4")
    copyfile(source_file, dest_path)
    return dest_path, None


def test_process_short_video(app: FastAPI, client: TestClient) -> None:
    def get_yt_handler_test() -> Callable[
        [str, str, dict[str, str] | None, int], Tuple[str | None, Enum | None]
    ]:
        return get_local_video

    app.dependency_overrides[get_yt_handler] = get_yt_handler_test
    resp = client.post(
        "/process", json={"youtube_url": "https://youtube.com/watch?v=short123"}
    )
    assert resp.status_code == 200
