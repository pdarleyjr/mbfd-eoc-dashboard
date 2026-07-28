import asyncio
import random
from datetime import UTC, datetime, timedelta

import httpx
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from redis.asyncio import Redis

from .adapters.base import Adapter
from .config import get_settings
from .database import SessionFactory
from .ingestion import IngestionRunner
from .logging_config import configure_logging
from .registry import source_registry
from .repository import Repository

logger = structlog.get_logger()

MIN_MISFIRE_GRACE_SECONDS = 60
MAX_MISFIRE_GRACE_SECONDS = 600


def misfire_grace_seconds(adapter: Adapter) -> int:
    """Allow a delayed source to run once after bounded scheduler contention."""
    expected_attempt_seconds = int(adapter.timeout_seconds * (adapter.retry_count + 1)) + 10
    return min(
        MAX_MISFIRE_GRACE_SECONDS,
        max(MIN_MISFIRE_GRACE_SECONDS, expected_attempt_seconds),
    )


async def reconcile_configured_sources(adapters: list[Adapter]) -> None:
    async with SessionFactory() as session:
        await Repository(session).retire_unconfigured_sources(
            {adapter.source_id for adapter in adapters}
        )


async def main() -> None:
    configure_logging()
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    headers = {"User-Agent": settings.user_agent, "Accept": "application/json"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        runner = IngestionRunner(redis, client, settings)
        scheduler = AsyncIOScheduler(timezone="UTC")
        adapters = source_registry()
        await reconcile_configured_sources(adapters)

        async def poll(adapter: Adapter) -> None:
            await runner.run(adapter)
            if adapter.source_id.startswith("pulsepoint"):
                has_active = await redis.get("eoc:pulsepoint:has-active") == "1"
                interval = 15 if has_active else 45
                scheduler.reschedule_job(
                    adapter.source_id,
                    trigger="interval",
                    seconds=interval,
                    jitter=max(1, int(interval * adapter.jitter_fraction)),
                )
            await redis.set("eoc:worker:last-heartbeat", datetime.now(UTC).isoformat(), ex=120)

        for index, adapter in enumerate(adapters):
            initial_spread = min(adapter.poll_interval_seconds, 90)
            initial_delay = (index * 2 + random.random()) % initial_spread
            scheduler.add_job(
                poll,
                "interval",
                seconds=adapter.poll_interval_seconds,
                args=[adapter],
                id=adapter.source_id,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=misfire_grace_seconds(adapter),
                jitter=max(1, int(adapter.poll_interval_seconds * adapter.jitter_fraction)),
                next_run_time=datetime.now(UTC) + timedelta(seconds=initial_delay),
            )
        scheduler.start()
        logger.info("worker_started", source_count=len(adapters))
        try:
            await asyncio.Event().wait()
        finally:
            scheduler.shutdown(wait=False)
            await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
