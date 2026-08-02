from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.adapters.base import Adapter, FetchedPayload
from app.config import Settings
from app.errors import UpstreamSchemaError
from app.ingestion import MAX_CIRCUIT_COOLDOWN_SECONDS, IngestionRunner, circuit_cooldown_seconds
from app.schemas import (
    AuthorityLevel,
    CanonicalRecord,
    CircuitState,
    SourceHealth,
    SourceHealthState,
    SourceType,
)

NOW = datetime(2026, 7, 27, 14, tzinfo=UTC)


def record(state: str = "active") -> CanonicalRecord:
    return CanonicalRecord(
        id="dummy:1",
        source_id="dummy",
        source_name="Dummy Official Source",
        source_type=SourceType.OFFICIAL_API,
        authority_level=AuthorityLevel.AUTHORITATIVE,
        source_record_id="1",
        source_url="https://example.gov/data",
        title="Public record",
        category="pulsepoint_call",
        observed_at=NOW,
        published_at=None,
        retrieved_at=NOW,
        expires_at=None,
        stale=False,
        stale_reason=None,
        confidence=1,
        geography={},
        zip_scope=[],
        raw_snapshot_hash="0" * 64,
        schema_version=1,
        payload={"state": state},
    )


class DummyAdapter(Adapter):
    source_id = "pulsepoint"
    source_name = "PulsePoint advisory"
    source_type = SourceType.PULSEPOINT_ADVISORY.value
    authority_level = AuthorityLevel.ADVISORY.value
    category = "pulsepoint_call"
    url = "https://example.gov/data"
    poll_interval_seconds = 15
    stale_threshold_seconds = 90
    retry_count = 1
    circuit_breaker_threshold = 2

    def __init__(self, *, error: Exception | None = None, state: str = "active") -> None:
        self.error = error
        self.state = state
        self.fetch_count = 0

    async def fetch(self, _client: httpx.AsyncClient) -> FetchedPayload:
        self.fetch_count += 1
        if self.error:
            raise self.error
        return FetchedPayload(
            body=b'{"records":[]}',
            content_type="application/json",
            parsed={},
        )

    def normalize(self, _payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        item = record(self.state)
        return [item.model_copy(update={"raw_snapshot_hash": snapshot_hash})]


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.published: list[tuple[str, str]] = []

    async def set(self, key: str, value: str, **_kwargs: object) -> bool:
        self.values[key] = value
        return True

    async def publish(self, channel: str, value: str) -> int:
        self.published.append((channel, value))
        return 1


class FakeRepository:
    def __init__(self, *, has_records: bool = True) -> None:
        self.health: list[tuple[SourceHealth, datetime | None]] = []
        self.records: list[CanonicalRecord] = []
        self.stale_reason: str | None = None
        self.has_records = has_records
        self.snapshots: list[tuple[object, ...]] = []
        self.retired_record_ids: set[str] = set()

    async def save_snapshot(self, *args: object) -> None:
        self.snapshots.append(args)

    async def upsert_records(
        self,
        _source_id: str,
        records: list[CanonicalRecord],
        *,
        retire_missing: bool,
    ) -> int:
        assert retire_missing is True
        incoming_ids = {record.source_record_id for record in records}
        self.retired_record_ids.update(
            record.source_record_id
            for record in self.records
            if record.source_record_id not in incoming_ids
        )
        self.records = records
        return len(records)

    async def set_health(
        self,
        health: SourceHealth,
        *,
        circuit_open_until: datetime | None = None,
    ) -> None:
        self.health.append((health, circuit_open_until))

    async def source_record_count(self, _source_id: str) -> int:
        return 1 if self.has_records else 0

    async def mark_source_stale(self, _source_id: str, reason: str) -> None:
        self.stale_reason = reason


def runner(tmp_path: Path) -> tuple[IngestionRunner, FakeRedis]:
    redis = FakeRedis()
    settings = Settings(raw_snapshot_dir=tmp_path)
    return (
        IngestionRunner(redis, httpx.AsyncClient(), settings),  # type: ignore[arg-type]
        redis,
    )


@pytest.mark.parametrize(("state", "interval"), [("active", 15), ("recent", 45)])
async def test_successful_attempt_records_provenance_and_adaptive_interval(
    tmp_path: Path,
    state: str,
    interval: int,
) -> None:
    ingestion, redis = runner(tmp_path)
    repository = FakeRepository()

    count = await ingestion._attempt(DummyAdapter(state=state), repository, None)

    assert count == 1
    assert repository.health[-1][0].state is SourceHealthState.HEALTHY
    assert repository.health[-1][0].poll_interval_seconds == interval
    assert repository.snapshots
    assert redis.values["eoc:pulsepoint:has-active"] == ("1" if state == "active" else "0")
    assert redis.published == [("eoc:cache-invalidate", "pulsepoint")]
    await ingestion.client.aclose()


async def test_retry_failure_preserves_lkg_and_opens_circuit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ingestion, _ = runner(tmp_path)
    repository = FakeRepository(has_records=True)
    previous = SourceHealth(
        source_id="pulsepoint",
        source_name="PulsePoint advisory",
        state=SourceHealthState.UNAVAILABLE,
        last_attempt=NOW,
        last_success=NOW,
        last_authoritative_observation=NOW,
        poll_interval_seconds=15,
        consecutive_failures=1,
        last_known_good=True,
        authority_level=AuthorityLevel.ADVISORY,
        circuit_breaker_state=CircuitState.CLOSED,
    )

    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("app.ingestion.asyncio.sleep", no_sleep)
    adapter = DummyAdapter(error=UpstreamSchemaError("upstream schema changed"))
    count = await ingestion._attempt(adapter, repository, previous)

    health, open_until = repository.health[-1]
    assert count == 0
    assert adapter.fetch_count == 2
    assert health.state is SourceHealthState.INVALID_RESPONSE
    assert health.last_known_good is True
    assert health.circuit_breaker_state is CircuitState.OPEN
    assert open_until is not None
    assert repository.stale_reason is not None
    assert "Showing cached information" in repository.stale_reason
    await ingestion.client.aclose()


async def test_failed_poll_preserves_lkg_then_success_retires_absent_membership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ingestion, _ = runner(tmp_path)
    repository = FakeRepository(has_records=True)
    repository.records = [record().model_copy(update={"source_record_id": "old-active"})]
    previous = SourceHealth(
        source_id="pulsepoint",
        source_name="PulsePoint advisory",
        state=SourceHealthState.HEALTHY,
        last_attempt=NOW,
        last_success=NOW,
        last_authoritative_observation=NOW,
        poll_interval_seconds=15,
        consecutive_failures=0,
        last_known_good=True,
        authority_level=AuthorityLevel.ADVISORY,
        circuit_breaker_state=CircuitState.CLOSED,
    )

    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("app.ingestion.asyncio.sleep", no_sleep)
    failed = DummyAdapter(error=httpx.ConnectTimeout("upstream unavailable"))
    assert await ingestion._attempt(failed, repository, previous) == 0
    assert [item.source_record_id for item in repository.records] == ["old-active"]
    assert repository.retired_record_ids == set()
    assert repository.stale_reason is not None

    failure_health = repository.health[-1][0]
    assert await ingestion._attempt(DummyAdapter(), repository, failure_health) == 1
    assert [item.source_record_id for item in repository.records] == ["1"]
    assert repository.retired_record_ids == {"old-active"}
    assert repository.health[-1][0].state is SourceHealthState.HEALTHY
    await ingestion.client.aclose()


async def test_layout_failure_and_safe_errors(tmp_path: Path) -> None:
    ingestion, _ = runner(tmp_path)
    repository = FakeRepository(has_records=False)
    adapter = DummyAdapter()

    await ingestion._record_failure(
        adapter,
        repository,
        None,
        UpstreamSchemaError("official page layout changed"),
    )

    assert repository.health[-1][0].state is SourceHealthState.SCRAPER_LAYOUT_CHANGED
    timeout = httpx.ReadTimeout("slow")
    response = httpx.Response(503, request=httpx.Request("GET", adapter.url))
    status = httpx.HTTPStatusError("bad", request=response.request, response=response)
    assert ingestion._safe_error(timeout) == "Source request timed out"
    assert ingestion._safe_error(status) == "Source returned HTTP 503"
    assert ingestion._safe_error(RuntimeError("secret")) == "Source temporarily unavailable"
    await ingestion.client.aclose()


def test_circuit_cooldown_does_not_suppress_slow_sources_for_days() -> None:
    fast = DummyAdapter()
    slow = DummyAdapter()
    slow.poll_interval_seconds = 86400

    assert circuit_cooldown_seconds(fast) == fast.poll_interval_seconds
    assert circuit_cooldown_seconds(slow) == MAX_CIRCUIT_COOLDOWN_SECONDS
