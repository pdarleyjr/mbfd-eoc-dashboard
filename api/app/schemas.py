from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceType(StrEnum):
    OFFICIAL_API = "official_api"
    OFFICIAL_GIS = "official_gis"
    OFFICIAL_FEED = "official_feed"
    PULSEPOINT_ADVISORY = "pulsepoint_advisory"
    OFFICIAL_WEB_SCRAPE = "official_web_scrape"


class AuthorityLevel(StrEnum):
    AUTHORITATIVE = "authoritative"
    ADVISORY = "advisory"
    SUPPLEMENTAL = "supplemental"


class SourceHealthState(StrEnum):
    HEALTHY = "healthy"
    DELAYED = "delayed"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    INVALID_RESPONSE = "invalid_response"
    SCRAPER_LAYOUT_CHANGED = "scraper_layout_changed"


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CanonicalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=3, max_length=300)
    source_id: str = Field(min_length=2, max_length=120)
    source_name: str = Field(min_length=2, max_length=240)
    source_type: SourceType
    authority_level: AuthorityLevel
    source_record_id: str = Field(min_length=1, max_length=500)
    source_url: str
    title: str = Field(min_length=1, max_length=1000)
    category: str = Field(min_length=2, max_length=120)
    observed_at: datetime | None = None
    published_at: datetime | None = None
    retrieved_at: datetime
    expires_at: datetime | None = None
    stale: bool = False
    stale_reason: str | None = None
    confidence: float = Field(ge=0, le=1)
    geography: dict[str, Any] = Field(default_factory=dict)
    zip_scope: list[str] = Field(default_factory=list)
    raw_snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    schema_version: int = Field(ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("observed_at", "published_at", "retrieved_at", "expires_at")
    @classmethod
    def require_aware_datetime(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps must include an explicit timezone")
        return value


class SourceHealth(BaseModel):
    source_id: str
    source_name: str
    state: SourceHealthState
    last_attempt: datetime | None = None
    last_success: datetime | None = None
    last_authoritative_observation: datetime | None = None
    current_data_age_seconds: int | None = None
    poll_interval_seconds: int
    consecutive_failures: int = 0
    last_known_good: bool = False
    authority_level: AuthorityLevel
    circuit_breaker_state: CircuitState = CircuitState.CLOSED
    schema_version: int = 1
    message: str | None = None


class ResponseMetadata(BaseModel):
    generated_at: datetime
    source_observation_time: datetime | None = None
    data_age_seconds: int | None = None
    stale: bool
    source_authority: list[AuthorityLevel]
    source_health: SourceHealthState
    last_successful_refresh: datetime | None = None
    empty_state: str | None = None


class RecordsResponse(BaseModel):
    metadata: ResponseMetadata
    records: list[CanonicalRecord]


class DashboardKpi(BaseModel):
    id: str
    label: str
    value: int | float | str | None
    unavailable: bool
    source: str
    updated_at: datetime | None
    detail_category: str


class DashboardSummary(BaseModel):
    metadata: ResponseMetadata
    kpis: list[DashboardKpi]
    records: list[CanonicalRecord]
    source_health: list[SourceHealth]


class VersionResponse(BaseModel):
    application: str = "mbfd-eoc-dashboard"
    release_sha: str
    build_id: str
    environment: str
    generated_at: datetime
