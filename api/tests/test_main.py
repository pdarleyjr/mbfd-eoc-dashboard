from fastapi.testclient import TestClient

from app.main import app


def test_security_policy_allows_official_fl511_map_images() -> None:
    response = TestClient(app, base_url="http://localhost").get("/health/live")

    assert response.status_code == 200
    content_security_policy = response.headers["Content-Security-Policy"]
    assert "img-src " in content_security_policy
    assert "https://images-dis.divas.cloud" in content_security_policy
    assert "https://tiles.ibi511.com" in content_security_policy
