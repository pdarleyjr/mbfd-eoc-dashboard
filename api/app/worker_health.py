import asyncio
from datetime import UTC, datetime

from dateutil.parser import isoparse
from redis.asyncio import Redis

from .config import get_settings


async def check() -> int:
    redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        value = await redis.get("eoc:worker:last-heartbeat")
        if not value:
            return 1
        age = (datetime.now(UTC) - isoparse(value)).total_seconds()
        return 0 if age < 120 else 1
    finally:
        await redis.aclose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(check()))
