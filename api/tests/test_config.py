import pytest

from app.config import Settings


def test_settings_default_to_disabled_gateway_grounding_contract() -> None:
    settings = Settings(_env_file=None)

    assert settings.ai_grounding_enabled is False
    assert str(settings.ai_gateway_url) == "http://172.20.0.1:11440/"
    assert settings.ai_capability == "mbfd-eoc-grounding"
    assert settings.ai_gateway_credential_file.as_posix() == ("/run/secrets/eoc-ai-gateway-token")
    assert not hasattr(settings, "ollama_url")
    assert not hasattr(settings, "ollama_model")
    assert settings.eia_api_key.get_secret_value() == ""


def test_settings_parse_csv_hosts_and_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EOC_ALLOWED_HOSTS", "eoc.mbfdhub.com, localhost,127.0.0.1")
    monkeypatch.setenv(
        "EOC_CORS_ORIGINS",
        "https://eoc.mbfdhub.com, https://operations.mbfdhub.com",
    )

    settings = Settings(_env_file=None)

    assert settings.allowed_hosts == ["eoc.mbfdhub.com", "localhost", "127.0.0.1"]
    assert settings.cors_origins == [
        "https://eoc.mbfdhub.com",
        "https://operations.mbfdhub.com",
    ]


def test_settings_keep_eia_key_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EOC_EIA_API_KEY", "server-secret")

    settings = Settings(_env_file=None)

    assert settings.eia_api_key.get_secret_value() == "server-secret"
    assert "server-secret" not in repr(settings)
