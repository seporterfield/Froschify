import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.fixture(scope="function", autouse=True)
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_smoke(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.text == "OK"
