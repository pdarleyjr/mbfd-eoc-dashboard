from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from app.schemas import CanonicalRecord


@dataclass(frozen=True)
class FetchedPayload:
    body: bytes
    content_type: str
    parsed: Any
    etag: str | None = None
    last_modified: str | None = None


class Adapter(ABC):
    source_id: str
    source_name: str
    source_type: str
    authority_level: str
    category: str
    url: str
    poll_interval_seconds: int
    stale_threshold_seconds: int
    schema_version: int = 1
    timeout_seconds: float = 20
    circuit_breaker_threshold: int = 3
    retry_count: int = 2
    jitter_fraction: float = 0.08
    last_known_good_retention_seconds: int = 604800
    retire_missing: bool = True
    geographic_filter: str = "Miami Beach boundary, ZIP 33139/33140, and buffered causeways"

    async def fetch(self, client: httpx.AsyncClient) -> FetchedPayload:
        response = await client.get(
            self.url,
            headers={"Accept": "application/json"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return FetchedPayload(
            body=response.content,
            content_type=response.headers.get("content-type", "application/octet-stream"),
            parsed=response.json(),
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

    @abstractmethod
    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        raise NotImplementedError
