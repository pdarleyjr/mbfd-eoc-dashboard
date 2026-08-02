from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import SpaStaticFiles, app


def test_security_policy_allows_official_fl511_map_images() -> None:
    response = TestClient(app, base_url="http://localhost").get("/health/live")

    assert response.status_code == 200
    content_security_policy = response.headers["Content-Security-Policy"]
    assert "img-src " in content_security_policy
    assert "https://images-dis.divas.cloud" in content_security_policy
    assert "https://tiles.ibi511.com" in content_security_policy


def static_spa(static_dir: Path) -> TestClient:
    static_dir.joinpath("index.html").write_text("<main>dashboard shell</main>", encoding="utf-8")
    test_app = FastAPI()
    test_app.mount("/", SpaStaticFiles(directory=static_dir, html=True), name="spa")
    return TestClient(test_app, base_url="http://localhost")


@pytest.mark.parametrize(
    "path",
    [
        "/api/unknown",
        "/health/unknown",
        "/metrics/unknown",
    ],
)
def test_spa_fallback_rejects_unknown_reserved_namespaces(tmp_path: Path, path: str) -> None:
    response = static_spa(tmp_path).get(path)

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Not found"}


def test_spa_fallback_preserves_extensionless_client_routes(tmp_path: Path) -> None:
    response = static_spa(tmp_path).get("/operations/map")

    assert response.status_code == 200
    assert response.text == "<main>dashboard shell</main>"
