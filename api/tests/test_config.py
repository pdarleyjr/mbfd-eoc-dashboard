import pytest

from app.config import Settings


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
