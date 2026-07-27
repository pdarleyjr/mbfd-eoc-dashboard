from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import pytest

from app import api
from app.schemas import (
    AuthorityLevel,
    CanonicalRecord,
    CircuitState,
    SourceHealth,
    SourceHealthState,
    SourceType,
)

HASH = "a" * 64
NOW = datetime(2026, 7, 27, 14, tzinfo=UTC)


def make_record(
    category: str = "weather_alert",
    *,
    source_id: str = "test-source",
    stale: bool = False,
    payload: dict[str, Any] | None = None,
) -> CanonicalRecord:
    return CanonicalRecord(
        id=f"{source_id}:{category}",
        source_id=source_id,
        source_name="Official Test Source",
        source_type=SourceType.OFFICIAL_API,
        authority_level=AuthorityLevel.AUTHORITATIVE,
        source_record_id=category,
        source_url="https://example.gov/data",
        title=f"Test {category}",
        category=category,
        observed_at=NOW - timedelta(minutes=2),
        published_at=None,
        retrieved_at=NOW,
        expires_at=NOW + timedelta(hours=1),
        stale=stale,
        stale_reason="refresh failed" if stale else None,
        confidence=1,
        geography={},
        zip_scope=["33139"],
        raw_snapshot_hash=HASH,
        schema_version=1,
        payload=payload or {},
    )


def make_health(
    state: SourceHealthState = SourceHealthState.HEALTHY,
) -> SourceHealth:
    return SourceHealth(
        source_id="test-source",
        source_name="Official Test Source",
        state=state,
        last_attempt=NOW,
        last_success=NOW,
        last_authoritative_observation=NOW - timedelta(minutes=2),
        poll_interval_seconds=45,
        consecutive_failures=0,
        last_known_good=True,
        authority_level=AuthorityLevel.AUTHORITATIVE,
        circuit_breaker_state=CircuitState.CLOSED,
    )


class FakeRepository:
    records: ClassVar[list[CanonicalRecord]] = []
    health: ClassVar[list[SourceHealth]] = []
    categories: ClassVar[list[str] | None] = None

    def __init__(self, _session: object) -> None:
        pass

    async def list_records(
        self,
        categories: list[str] | None = None,
        *,
        include_expired: bool = False,
        limit: int = 1000,
    ) -> list[CanonicalRecord]:
        del include_expired, limit
        type(self).categories = categories
        if not categories:
            return self.records
        return [record for record in self.records if record.category in categories]

    async def list_health(self) -> list[SourceHealth]:
        return self.health


@pytest.mark.parametrize(
    ("endpoint", "group"),
    [
        (api.incidents, "incidents"),
        (api.weather, "weather"),
        (api.coastal, "coastal"),
        (api.tropical, "tropical"),
        (api.traffic, "traffic"),
        (api.utilities, "utilities"),
        (api.shelters, "shelters"),
        (api.facilities, "facilities"),
        (api.transit, "transit"),
        (api.notices, "notices"),
        (api.map_features, "map"),
    ],
)
async def test_group_endpoints_use_declared_categories(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: Any,
    group: str,
) -> None:
    FakeRepository.records = [make_record()]
    FakeRepository.health = [make_health()]
    monkeypatch.setattr(api, "Repository", FakeRepository)

    response = await endpoint(object())

    assert FakeRepository.categories == api.CATEGORY_GROUPS[group]
    assert response.metadata.source_health is SourceHealthState.HEALTHY


async def test_dashboard_summary_counts_only_supported_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeRepository.records = [
        make_record("pulsepoint_call", payload={"state": "active"}),
        make_record("weather_alert"),
        make_record("lane_closure"),
        make_record("open_shelter"),
        make_record("power_outage_summary", payload={"Pct_Out": 1.25}),
    ]
    FakeRepository.health = [make_health()]
    monkeypatch.setattr(api, "Repository", FakeRepository)

    summary = await api.dashboard_summary(object())

    assert [item.value for item in summary.kpis] == [1, 1, 1, 1, 1.25, 1]
    assert all(not item.unavailable for item in summary.kpis)


async def test_dashboard_summary_marks_power_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeRepository.records = []
    FakeRepository.health = [make_health(SourceHealthState.UNAVAILABLE)]
    monkeypatch.setattr(api, "Repository", FakeRepository)

    summary = await api.dashboard_summary(object())

    power = next(item for item in summary.kpis if item.id == "power")
    assert power.unavailable is True
    assert summary.metadata.empty_state == "No current records returned by source"
    assert summary.metadata.source_health is SourceHealthState.UNAVAILABLE


async def test_source_health_and_version(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeRepository.health = [make_health()]
    monkeypatch.setattr(api, "Repository", FakeRepository)

    health = await api.source_health(object())
    version = await api.version()

    assert health[0].source_id == "test-source"
    assert version.application == "mbfd-eoc-dashboard"


def test_metadata_prioritizes_stale_and_delayed_states() -> None:
    stale = api._metadata([make_record(stale=True)], [make_health()])
    delayed = api._metadata(
        [make_record()],
        [make_health(SourceHealthState.INVALID_RESPONSE)],
    )

    assert stale.source_health is SourceHealthState.STALE
    assert stale.stale is True
    assert stale.data_age_seconds is not None
    assert delayed.source_health is SourceHealthState.DELAYED
