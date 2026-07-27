"""Read-only live contract probe for every configured public source."""

import asyncio
import json
from dataclasses import asdict, dataclass

import httpx

from app.config import get_settings
from app.registry import source_registry


@dataclass
class ProbeResult:
    source_id: str
    status: str
    record_count: int | None
    detail: str


async def probe(adapter, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> ProbeResult:
    async with semaphore:
        try:
            fetched = await adapter.fetch(client)
            records = adapter.normalize(fetched.parsed, "0" * 64)
            return ProbeResult(adapter.source_id, "valid", len(records), "schema accepted")
        except httpx.HTTPStatusError as exc:
            return ProbeResult(
                adapter.source_id,
                "http_error",
                None,
                f"HTTP {exc.response.status_code}",
            )
        except httpx.TimeoutException:
            return ProbeResult(adapter.source_id, "timeout", None, "request timed out")
        except Exception as exc:
            return ProbeResult(
                adapter.source_id,
                "invalid",
                None,
                f"{type(exc).__name__}: {str(exc)[:180]}",
            )


async def main() -> int:
    settings = get_settings()
    headers = {"User-Agent": settings.user_agent, "Accept": "application/json"}
    semaphore = asyncio.Semaphore(4)
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        results = await asyncio.gather(
            *(probe(adapter, client, semaphore) for adapter in source_registry())
        )
    results.sort(key=lambda result: result.source_id)
    print(json.dumps([asdict(result) for result in results], indent=2))
    return 0 if all(result.status == "valid" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
