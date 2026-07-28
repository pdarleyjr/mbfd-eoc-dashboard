import asyncio
import hashlib
import random
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import structlog
from redis.asyncio import Redis

from .adapters.base import Adapter, FetchedPayload
from .config import Settings, get_settings
from .database import SessionFactory
from .errors import UpstreamSchemaError
from .metrics import CACHE_EVENTS, SCHEDULER_LOCK, SOURCE_POLL_SECONDS, SOURCE_POLLS, SOURCE_RECORDS
from .repository import Repository
from .schemas import (
    AuthorityLevel,
    CircuitState,
    SourceHealth,
    SourceHealthState,
)

logger = structlog.get_logger()

MAX_CIRCUIT_COOLDOWN_SECONDS = 900


def circuit_cooldown_seconds(adapter: Adapter) -> int:
    """Bound restart-time circuit suppression for infrequently polled sources."""
    return max(1, min(adapter.poll_interval_seconds, MAX_CIRCUIT_COOLDOWN_SECONDS))


class IngestionRunner:
    def __init__(
        self,
        redis: Redis,
        client: httpx.AsyncClient,
        settings: Settings | None = None,
    ) -> None:
        self.redis = redis
        self.client = client
        self.settings = settings or get_settings()

    async def run(self, adapter: Adapter) -> int | None:
        lock = self.redis.lock(
            f"eoc:ingest-lock:{adapter.source_id}",
            timeout=max(60, adapter.timeout_seconds * (adapter.retry_count + 2)),
            blocking_timeout=0,
        )
        acquired = await lock.acquire(blocking=False)
        SCHEDULER_LOCK.labels(adapter.source_id).set(1 if acquired else 0)
        if not acquired:
            logger.info("source_poll_skipped_lock", source_id=adapter.source_id)
            return None
        started = time.monotonic()
        try:
            async with SessionFactory() as session:
                repository = Repository(session)
                previous = await repository.get_health(adapter.source_id)
                if (
                    previous
                    and previous.circuit_breaker_state is CircuitState.OPEN
                    and previous.last_attempt
                    and datetime.now(UTC)
                    < previous.last_attempt + timedelta(seconds=circuit_cooldown_seconds(adapter))
                ):
                    logger.info("source_poll_skipped_circuit", source_id=adapter.source_id)
                    return None
                return await self._attempt(adapter, repository, previous)
        finally:
            SOURCE_POLL_SECONDS.labels(adapter.source_id).observe(time.monotonic() - started)
            try:
                await lock.release()
            except Exception:
                logger.warning("source_lock_release_failed", source_id=adapter.source_id)
            SCHEDULER_LOCK.labels(adapter.source_id).set(0)

    async def _attempt(
        self,
        adapter: Adapter,
        repository: Repository,
        previous: SourceHealth | None,
    ) -> int:
        last_error: Exception | None = None
        for attempt in range(adapter.retry_count + 1):
            try:
                fetched = await adapter.fetch(self.client)
                snapshot_hash, path = self._save_snapshot(adapter, fetched)
                await repository.save_snapshot(
                    adapter.source_id,
                    snapshot_hash,
                    datetime.now(UTC),
                    fetched.content_type,
                    len(fetched.body),
                    str(path),
                )
                records = adapter.normalize(fetched.parsed, snapshot_hash)
                effective_poll_interval = adapter.poll_interval_seconds
                if adapter.source_id.startswith("pulsepoint"):
                    has_active = any(item.payload.get("state") == "active" for item in records)
                    effective_poll_interval = 15 if has_active else 45
                    await self.redis.set(
                        "eoc:pulsepoint:has-active",
                        "1" if has_active else "0",
                        ex=120,
                    )
                count = await repository.upsert_records(
                    adapter.source_id,
                    records,
                    retire_missing=adapter.retire_missing,
                )
                observation_times: list[datetime] = []
                for item in records:
                    observation = item.observed_at or item.published_at
                    if observation is not None:
                        observation_times.append(observation)
                now = datetime.now(UTC)
                await repository.set_health(
                    SourceHealth(
                        source_id=adapter.source_id,
                        source_name=adapter.source_name,
                        state=SourceHealthState.HEALTHY,
                        last_attempt=now,
                        last_success=now,
                        last_authoritative_observation=max(observation_times, default=None),
                        poll_interval_seconds=effective_poll_interval,
                        consecutive_failures=0,
                        last_known_good=bool(count),
                        authority_level=AuthorityLevel(adapter.authority_level),
                        circuit_breaker_state=CircuitState.CLOSED,
                        schema_version=adapter.schema_version,
                        message=(None if count else "No current records returned by source"),
                    )
                )
                await self.redis.set(
                    f"eoc:last-success:{adapter.source_id}", now.isoformat(), ex=604800
                )
                await self.redis.publish("eoc:cache-invalidate", adapter.source_id)
                CACHE_EVENTS.labels("invalidate").inc()
                SOURCE_POLLS.labels(adapter.source_id, "success").inc()
                SOURCE_RECORDS.labels(adapter.source_id).set(count)
                logger.info("source_poll_success", source_id=adapter.source_id, record_count=count)
                return count
            except (httpx.HTTPError, UpstreamSchemaError, ValueError, TypeError) as exc:
                last_error = exc
                if attempt < adapter.retry_count:
                    delay = min(8.0, (2**attempt) + random.random())
                    await asyncio.sleep(delay)
        assert last_error is not None
        return await self._record_failure(adapter, repository, previous, last_error)

    async def _record_failure(
        self,
        adapter: Adapter,
        repository: Repository,
        previous: SourceHealth | None,
        error: Exception,
    ) -> int:
        failures = (previous.consecutive_failures if previous else 0) + 1
        has_lkg = bool(await repository.source_record_count(adapter.source_id))
        await repository.mark_source_stale(
            adapter.source_id,
            f"Showing cached information; refresh failed at {datetime.now(UTC).isoformat()}",
        )
        is_layout = isinstance(error, UpstreamSchemaError) and "layout" in str(error).lower()
        is_schema = isinstance(error, UpstreamSchemaError)
        state = (
            SourceHealthState.SCRAPER_LAYOUT_CHANGED
            if is_layout
            else SourceHealthState.INVALID_RESPONSE
            if is_schema
            else SourceHealthState.UNAVAILABLE
        )
        circuit = (
            CircuitState.OPEN
            if failures >= adapter.circuit_breaker_threshold
            else CircuitState.CLOSED
        )
        now = datetime.now(UTC)
        await repository.set_health(
            SourceHealth(
                source_id=adapter.source_id,
                source_name=adapter.source_name,
                state=state,
                last_attempt=now,
                last_success=previous.last_success if previous else None,
                last_authoritative_observation=(
                    previous.last_authoritative_observation if previous else None
                ),
                poll_interval_seconds=adapter.poll_interval_seconds,
                consecutive_failures=failures,
                last_known_good=has_lkg,
                authority_level=AuthorityLevel(adapter.authority_level),
                circuit_breaker_state=circuit,
                schema_version=adapter.schema_version,
                message=self._safe_error(error),
            ),
            circuit_open_until=(
                now + timedelta(seconds=circuit_cooldown_seconds(adapter))
                if circuit is CircuitState.OPEN
                else None
            ),
        )
        SOURCE_POLLS.labels(adapter.source_id, "failure").inc()
        logger.warning(
            "source_poll_failure",
            source_id=adapter.source_id,
            state=state.value,
            failures=failures,
            circuit=circuit.value,
            error_type=type(error).__name__,
        )
        return 0

    def _save_snapshot(self, adapter: Adapter, fetched: FetchedPayload) -> tuple[str, Path]:
        digest = hashlib.sha256(fetched.body).hexdigest()
        directory = self.settings.raw_snapshot_dir / adapter.source_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{digest}.snapshot"
        if not path.exists():
            path.write_bytes(fetched.body)
        return digest, path

    @staticmethod
    def _safe_error(error: Exception) -> str:
        if isinstance(error, UpstreamSchemaError):
            return str(error)[:300]
        if isinstance(error, httpx.TimeoutException):
            return "Source request timed out"
        if isinstance(error, httpx.HTTPStatusError):
            return f"Source returned HTTP {error.response.status_code}"
        return "Source temporarily unavailable"
