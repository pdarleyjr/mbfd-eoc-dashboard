from datetime import UTC, datetime, timedelta
from typing import Any

from app.models import CanonicalRecordRow, SourceHealthRow
from app.repository import Repository, _record_values
from app.schemas import (
    AuthorityLevel,
    CanonicalRecord,
    CircuitState,
    SourceHealth,
    SourceHealthState,
    SourceType,
)

NOW = datetime.now(UTC)


def canonical() -> CanonicalRecord:
    return CanonicalRecord(
        id="source:one",
        source_id="source",
        source_name="Official Source",
        source_type=SourceType.OFFICIAL_GIS,
        authority_level=AuthorityLevel.AUTHORITATIVE,
        source_record_id="one",
        source_url="https://example.gov",
        title="Record one",
        category="lane_closure",
        observed_at=NOW,
        published_at=None,
        retrieved_at=NOW,
        expires_at=NOW + timedelta(hours=1),
        stale=False,
        stale_reason=None,
        confidence=1,
        geography={"type": "Point", "coordinates": [-80.13, 25.79]},
        zip_scope=["33139"],
        raw_snapshot_hash="b" * 64,
        schema_version=1,
        payload={"status": "open"},
    )


def record_row() -> CanonicalRecordRow:
    values = canonical().model_dump(mode="python")
    values["source_type"] = SourceType.OFFICIAL_GIS.value
    values["authority_level"] = AuthorityLevel.AUTHORITATIVE.value
    return CanonicalRecordRow(**values, geom=None)


def health_row() -> SourceHealthRow:
    return SourceHealthRow(
        source_id="source",
        source_name="Official Source",
        state=SourceHealthState.HEALTHY.value,
        last_attempt=NOW,
        last_success=NOW,
        last_authoritative_observation=NOW,
        poll_interval_seconds=60,
        consecutive_failures=0,
        last_known_good=True,
        authority_level=AuthorityLevel.AUTHORITATIVE.value,
        circuit_breaker_state=CircuitState.CLOSED.value,
        circuit_open_until=None,
        schema_version=1,
        message=None,
    )


class ScalarRows:
    def __init__(self, rows: list[Any]) -> None:
        self.rows = rows

    def all(self) -> list[Any]:
        return self.rows

    def __iter__(self):
        return iter(self.rows)


class FakeSession:
    def __init__(
        self,
        *,
        scalar_sets: list[list[Any]] | None = None,
        get_value: Any = None,
        count: int | None = 0,
    ) -> None:
        self.scalar_sets = scalar_sets or []
        self.get_value = get_value
        self.count = count
        self.executed: list[Any] = []
        self.commits = 0

    async def execute(self, statement: Any) -> None:
        self.executed.append(statement)

    async def scalars(self, _statement: Any) -> ScalarRows:
        return ScalarRows(self.scalar_sets.pop(0) if self.scalar_sets else [])

    async def get(self, _model: Any, _identity: str) -> Any:
        return self.get_value

    async def scalar(self, _statement: Any) -> int | None:
        return self.count

    async def commit(self) -> None:
        self.commits += 1


async def test_upsert_records_and_retire_absent_rows() -> None:
    absent = record_row()
    absent.source_record_id = "old"
    original_expiry = absent.expires_at
    session = FakeSession(scalar_sets=[[absent]])
    repository = Repository(session)  # type: ignore[arg-type]

    count = await repository.upsert_records("source", [canonical()], retire_missing=True)

    assert count == 1
    assert len(session.executed) == 1
    assert absent.stale is True
    assert absent.expires_at is not None
    assert original_expiry is not None
    assert absent.expires_at < original_expiry
    assert session.commits == 1


async def test_successful_empty_response_retires_previous_rows() -> None:
    absent = record_row()
    session = FakeSession(scalar_sets=[[absent]])
    repository = Repository(session)  # type: ignore[arg-type]

    count = await repository.upsert_records("source", [], retire_missing=True)

    assert count == 0
    assert absent.stale is True
    assert absent.expires_at is not None
    assert session.commits == 1


async def test_read_records_and_source_health() -> None:
    session = FakeSession(scalar_sets=[[record_row()], [health_row()]])
    repository = Repository(session)  # type: ignore[arg-type]

    records = await repository.list_records(["lane_closure"])
    health = await repository.list_health()

    assert records == [canonical()]
    assert health[0].state is SourceHealthState.HEALTHY
    assert health[0].current_data_age_seconds is not None


async def test_get_health_present_and_missing() -> None:
    present = Repository(FakeSession(get_value=health_row()))  # type: ignore[arg-type]
    missing = Repository(FakeSession())  # type: ignore[arg-type]

    assert (await present.get_health("source")).source_id == "source"  # type: ignore[union-attr]
    assert await missing.get_health("missing") is None


async def test_mutation_helpers_commit_expected_statements() -> None:
    row = record_row()
    session = FakeSession(scalar_sets=[[row]], count=3)
    repository = Repository(session)  # type: ignore[arg-type]

    await repository.mark_source_stale("source", "refresh failed")
    assert row.stale is True
    assert row.stale_reason == "refresh failed"
    assert await repository.source_record_count("source") == 3
    await repository.save_snapshot(
        "source",
        "c" * 64,
        NOW,
        "application/json",
        100,
        "/snapshots/source",
    )
    await repository.set_health(
        SourceHealth(
            source_id="source",
            source_name="Official Source",
            state=SourceHealthState.HEALTHY,
            last_attempt=NOW,
            last_success=NOW,
            last_authoritative_observation=NOW,
            poll_interval_seconds=60,
            last_known_good=True,
            authority_level=AuthorityLevel.AUTHORITATIVE,
        )
    )
    await repository.delete_source_records("source")

    assert session.commits == 4
    assert len(session.executed) == 3


def test_record_values_builds_postgis_expression() -> None:
    values = _record_values(canonical())
    assert values["source_type"] == "official_gis"
    assert values["authority_level"] == "authoritative"
    assert values["geom"] is not None
