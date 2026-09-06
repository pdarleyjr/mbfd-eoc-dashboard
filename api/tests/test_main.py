import inspect

from fastapi.testclient import TestClient

from app.main import app, ready


def test_security_policy_allows_official_fl511_map_images() -> None:
    response = TestClient(app, base_url="http://localhost").get("/health/live")

    assert response.status_code == 200
    content_security_policy = response.headers["Content-Security-Policy"]
    assert "img-src " in content_security_policy
    assert "https://images-dis.divas.cloud" in content_security_policy
    assert "https://tiles.ibi511.com" in content_security_policy


def test_core_readiness_has_no_ai_network_dependency() -> None:
    source = inspect.getsource(ready)

    assert "ollama" not in source.lower()
    assert "ai_gateway" not in source.lower()


def test_ai_readiness_is_separate_and_disabled_by_default() -> None:
    response = TestClient(app, base_url="http://localhost").get("/health/ai")

    assert response.status_code == 200
    assert response.json() == {
        "status": "disabled",
        "capability": "mbfd-eoc-grounding",
    }
