import hashlib
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

from app.errors import UpstreamSchemaError
from app.schemas import AuthorityLevel, CanonicalRecord, SourceType

from .base import Adapter, FetchedPayload
from .utils import compact_text, parse_datetime, stable_id, utc_now


@dataclass(frozen=True)
class OfficialWebSource:
    source_id: str
    source_name: str
    url: str
    selectors: tuple[str, ...]
    category: str = "official_notice"
    poll_interval_seconds: int = 300
    stale_threshold_seconds: int = 900
    relevance_terms: tuple[str, ...] = (
        "miami beach",
        "33139",
        "33140",
        "macarthur",
        "julia tuttle",
        "venetian",
    )


class OfficialWebAdapter(Adapter):
    source_type = SourceType.OFFICIAL_WEB_SCRAPE.value
    authority_level = AuthorityLevel.SUPPLEMENTAL.value
    schema_version = 1
    retire_missing = False
    timeout_seconds = 45

    def __init__(self, source: OfficialWebSource) -> None:
        self.source = source
        self.source_id = source.source_id
        self.source_name = source.source_name
        self.url = source.url
        self.category = source.category
        self.poll_interval_seconds = source.poll_interval_seconds
        self.stale_threshold_seconds = source.stale_threshold_seconds

    async def fetch(self, client: httpx.AsyncClient) -> FetchedPayload:
        response = await client.get(
            self.url,
            headers={"Accept": "text/html,application/xhtml+xml"},
            timeout=self.timeout_seconds,
            follow_redirects=True,
        )
        response.raise_for_status()
        return FetchedPayload(
            body=response.content,
            content_type=response.headers.get("content-type", "text/html"),
            parsed=response.text,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        if not isinstance(payload, str) or not payload.strip():
            raise UpstreamSchemaError("Official webpage returned empty content")
        soup = BeautifulSoup(payload, "html.parser")
        nodes: list[Tag] = []
        for selector in self.source.selectors:
            nodes.extend(soup.select(selector))
        unique_nodes = list(dict.fromkeys(nodes))
        if not unique_nodes:
            raise UpstreamSchemaError("Official webpage layout may have changed")
        retrieved = utc_now()
        records: list[CanonicalRecord] = []
        seen: set[str] = set()
        for node in unique_nodes:
            text = compact_text(node.get_text(" ", strip=True), 5000)
            if not text or text in seen:
                continue
            seen.add(text)
            lowered = text.lower()
            if self.source.relevance_terms and not any(
                term in lowered for term in self.source.relevance_terms
            ):
                continue
            heading = node.find(["h1", "h2", "h3", "h4"])
            time_node = node.find("time")
            link = node.find("a", href=True)
            href = link.get("href") if isinstance(link, Tag) else None
            source_url = (
                urljoin(self.source.url, href) if isinstance(href, str) else self.source.url
            )
            source_record_id = hashlib.sha256(text.encode("utf-8")).hexdigest()
            records.append(
                CanonicalRecord(
                    id=stable_id(self.source_id, source_record_id),
                    source_id=self.source_id,
                    source_name=self.source_name,
                    source_type=SourceType.OFFICIAL_WEB_SCRAPE,
                    authority_level=AuthorityLevel.SUPPLEMENTAL,
                    source_record_id=source_record_id,
                    source_url=self.source.url,
                    title=compact_text(
                        heading.get_text(" ", strip=True) if heading else text, 1000
                    ),
                    category=self.category,
                    observed_at=None,
                    published_at=parse_datetime(time_node.get("datetime") if time_node else None),
                    retrieved_at=retrieved,
                    expires_at=None,
                    stale=False,
                    stale_reason=None,
                    confidence=1,
                    geography={},
                    zip_scope=[zipcode for zipcode in ("33139", "33140") if zipcode in text],
                    raw_snapshot_hash=snapshot_hash,
                    schema_version=1,
                    payload={
                        "text": text,
                        "source_type": "official_web_scrape",
                        "authority_level": "supplemental",
                        "retrieval_time": retrieved.isoformat(),
                        "article_url": source_url,
                    },
                )
            )
        return records
