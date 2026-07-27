from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas import (
    AuthorityLevel,
    CanonicalRecord,
    SourceHealthState,
    SourceType,
)


def record() -> CanonicalRecord:
    return CanonicalRecord(
        id="nws-alerts:abc",
        source_id="nws-alerts",
        source_name="National Weather Service",
        source_type=SourceType.OFFICIAL_API,
        authority_level=AuthorityLevel.AUTHORITATIVE,
        source_record_id="abc",
        source_url="https://api.weather.gov/alerts/abc",
        title="Coastal Flood Advisory",
        category="weather_alert",
        observed_at=None,
        published_at=datetime(2026, 7, 27, 13, tzinfo=UTC),
        retrieved_at=datetime(2026, 7, 27, 13, 1, tzinfo=UTC),
        expires_at=datetime(2026, 7, 27, 20, tzinfo=UTC),
        stale=False,
        stale_reason=None,
        confidence=1,
        geography={},
        zip_scope=["33139", "33140"],
        raw_snapshot_hash="a" * 64,
        schema_version=1,
        payload={},
    )


def test_canonical_record_accepts_provenance_envelope() -> None:
    assert record().authority_level is AuthorityLevel.AUTHORITATIVE


def test_canonical_record_requires_timezone_aware_retrieval_time() -> None:
    payload = record().model_dump()
    payload["retrieved_at"] = datetime(2026, 7, 27, 13, 1)  # noqa: DTZ001
    with pytest.raises(ValidationError):
        CanonicalRecord.model_validate(payload)


def test_source_health_has_honest_non_normal_states() -> None:
    assert {state.value for state in SourceHealthState} == {
        "healthy",
        "delayed",
        "stale",
        "unavailable",
        "invalid_response",
        "scraper_layout_changed",
    }
