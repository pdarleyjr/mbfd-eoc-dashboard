from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EOC_",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    release_sha: str = "development"
    build_id: str = "local"
    public_origin: AnyHttpUrl = AnyHttpUrl("http://localhost:8220")
    database_url: str = "postgresql+asyncpg://eoc:eoc@localhost:5432/eoc"
    redis_url: str = "redis://localhost:6379/0"
    pulsepoint_url: AnyHttpUrl = AnyHttpUrl(
        "https://pulsepoint-proxy.pdarleyjr.workers.dev/incidents"
    )
    ollama_url: AnyHttpUrl = AnyHttpUrl("http://host.docker.internal:11434")
    ollama_model: str = "qwen3.6:35b"
    maxun_url: AnyHttpUrl = AnyHttpUrl("http://eoc-maxun-backend:8080")
    maxun_enabled: bool = False
    hermes_health_url: str = ""
    sentry_dsn: str = ""
    user_agent: str = "MBFD-EOC/1.0 (operations-contact@mbfdhub.com)"
    docs_enabled: bool = True
    rate_limit_per_minute: int = 240
    raw_snapshot_dir: Path = Path("data/raw-snapshots")
    static_dir: Path | None = None
    allowed_hosts: Annotated[list[str], NoDecode] = [
        "localhost",
        "127.0.0.1",
        "eoc.mbfdhub.com",
    ]
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("allowed_hosts", "cors_origins", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @property
    def production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
