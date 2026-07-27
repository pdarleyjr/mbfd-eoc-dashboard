import json
from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CanonicalRecordRow, RawSnapshotRow, SourceHealthRow
from .schemas import (
    AuthorityLevel,
    CanonicalRecord,
    CircuitState,
    SourceHealth,
    SourceHealthState,
)


def _record_values(record: CanonicalRecord) -> dict[str, object]:
    values = record.model_dump(mode="python")
    values["source_type"] = record.source_type.value
    values["authority_level"] = record.authority_level.value
    values["geom"] = (
        func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(record.geography)), 4326)
        if record.geography.get("type")
        else None
    )
    return values


class Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_records(
        self,
        source_id: str,
        records: Iterable[CanonicalRecord],
        *,
        retire_missing: bool,
    ) -> int:
        rows = list(records)
        seen: set[str] = set()
        for record in rows:
            seen.add(record.source_record_id)
            statement = insert(CanonicalRecordRow).values(**_record_values(record))
            statement = statement.on_conflict_do_update(
                index_elements=["source_id", "source_record_id"],
                set_={
                    key: value
                    for key, value in _record_values(record).items()
                    if key not in {"id", "source_id", "source_record_id"}
                },
            )
            await self.session.execute(statement)
        if retire_missing and seen:
            existing = await self.session.scalars(
                select(CanonicalRecordRow).where(
                    CanonicalRecordRow.source_id == source_id,
                    CanonicalRecordRow.source_record_id.not_in(seen),
                )
            )
            now = datetime.now(UTC)
            for row in existing:
                row.expires_at = row.expires_at or now
                row.stale = True
                row.stale_reason = "Record absent from a successful current source response"
        await self.session.commit()
        return len(rows)

    async def list_records(
        self,
        categories: list[str] | None = None,
        *,
        include_expired: bool = False,
        limit: int = 1000,
    ) -> list[CanonicalRecord]:
        query = select(CanonicalRecordRow)
        if categories:
            query = query.where(CanonicalRecordRow.category.in_(categories))
        if not include_expired:
            now = datetime.now(UTC)
            query = query.where(
                (CanonicalRecordRow.expires_at.is_(None)) | (CanonicalRecordRow.expires_at > now)
            )
        query = query.order_by(
            func.coalesce(
                CanonicalRecordRow.observed_at,
                CanonicalRecordRow.published_at,
                CanonicalRecordRow.retrieved_at,
            ).desc()
        ).limit(limit)
        rows = (await self.session.scalars(query)).all()
        return [self._to_record(row) for row in rows]

    async def list_health(self) -> list[SourceHealth]:
        rows = (
            await self.session.scalars(
                select(SourceHealthRow).order_by(SourceHealthRow.source_name)
            )
        ).all()
        now = datetime.now(UTC)
        return [
            SourceHealth(
                source_id=row.source_id,
                source_name=row.source_name,
                state=SourceHealthState(row.state),
                last_attempt=row.last_attempt,
                last_success=row.last_success,
                last_authoritative_observation=row.last_authoritative_observation,
                current_data_age_seconds=(
                    max(0, int((now - row.last_authoritative_observation).total_seconds()))
                    if row.last_authoritative_observation
                    else None
                ),
                poll_interval_seconds=row.poll_interval_seconds,
                consecutive_failures=row.consecutive_failures,
                last_known_good=row.last_known_good,
                authority_level=AuthorityLevel(row.authority_level),
                circuit_breaker_state=CircuitState(row.circuit_breaker_state),
                schema_version=row.schema_version,
                message=row.message,
            )
            for row in rows
        ]

    async def get_health(self, source_id: str) -> SourceHealth | None:
        row = await self.session.get(SourceHealthRow, source_id)
        if row is None:
            return None
        now = datetime.now(UTC)
        return SourceHealth(
            source_id=row.source_id,
            source_name=row.source_name,
            state=SourceHealthState(row.state),
            last_attempt=row.last_attempt,
            last_success=row.last_success,
            last_authoritative_observation=row.last_authoritative_observation,
            current_data_age_seconds=(
                max(0, int((now - row.last_authoritative_observation).total_seconds()))
                if row.last_authoritative_observation
                else None
            ),
            poll_interval_seconds=row.poll_interval_seconds,
            consecutive_failures=row.consecutive_failures,
            last_known_good=row.last_known_good,
            authority_level=AuthorityLevel(row.authority_level),
            circuit_breaker_state=CircuitState(row.circuit_breaker_state),
            schema_version=row.schema_version,
            message=row.message,
        )

    async def mark_source_stale(self, source_id: str, reason: str) -> None:
        rows = await self.session.scalars(
            select(CanonicalRecordRow).where(CanonicalRecordRow.source_id == source_id)
        )
        for row in rows:
            row.stale = True
            row.stale_reason = reason
        await self.session.commit()

    async def source_record_count(self, source_id: str) -> int:
        count = await self.session.scalar(
            select(func.count())
            .select_from(CanonicalRecordRow)
            .where(CanonicalRecordRow.source_id == source_id)
        )
        return int(count or 0)

    async def save_snapshot(
        self,
        source_id: str,
        sha256: str,
        retrieved_at: datetime,
        content_type: str,
        byte_count: int,
        storage_path: str,
    ) -> None:
        statement = insert(RawSnapshotRow).values(
            source_id=source_id,
            sha256=sha256,
            retrieved_at=retrieved_at,
            content_type=content_type,
            byte_count=byte_count,
            storage_path=storage_path,
        )
        await self.session.execute(statement.on_conflict_do_nothing())
        await self.session.commit()

    async def set_health(
        self, health: SourceHealth, *, circuit_open_until: datetime | None = None
    ) -> None:
        values = health.model_dump(mode="python")
        values["state"] = health.state.value
        values["authority_level"] = health.authority_level.value
        values["circuit_breaker_state"] = health.circuit_breaker_state.value
        values.pop("current_data_age_seconds", None)
        values["circuit_open_until"] = circuit_open_until
        statement = insert(SourceHealthRow).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=["source_id"],
            set_={key: value for key, value in values.items() if key != "source_id"},
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def delete_source_records(self, source_id: str) -> None:
        await self.session.execute(
            delete(CanonicalRecordRow).where(CanonicalRecordRow.source_id == source_id)
        )
        await self.session.commit()

    @staticmethod
    def _to_record(row: CanonicalRecordRow) -> CanonicalRecord:
        return CanonicalRecord.model_validate(
            {
                column.name: getattr(row, column.name)
                for column in CanonicalRecordRow.__table__.columns
                if column.name != "geom"
            }
        )
