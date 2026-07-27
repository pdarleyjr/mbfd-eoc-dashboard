from typing import Any

from app.errors import UpstreamSchemaError
from app.schemas import AuthorityLevel, CanonicalRecord, SourceType

from .base import Adapter
from .utils import compact_text, parse_datetime, stable_id, utc_now


class NhcCurrentStormsAdapter(Adapter):
    source_id = "nhc-current-storms"
    source_name = "National Hurricane Center"
    source_type = SourceType.OFFICIAL_FEED.value
    authority_level = AuthorityLevel.AUTHORITATIVE.value
    category = "tropical"
    url = "https://www.nhc.noaa.gov/CurrentStorms.json"
    poll_interval_seconds = 300
    stale_threshold_seconds = 900

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        if not isinstance(payload, dict):
            raise UpstreamSchemaError("NHC current storms response must be an object")
        storms = payload.get("activeStorms", [])
        if not isinstance(storms, list):
            raise UpstreamSchemaError("NHC activeStorms collection is invalid")
        retrieved = utc_now()
        records: list[CanonicalRecord] = []
        for storm in storms:
            if not isinstance(storm, dict):
                raise UpstreamSchemaError("NHC storm record is invalid")
            upstream_id = str(
                storm.get("id")
                or storm.get("atcfIdentifier")
                or storm.get("binNumber")
                or storm.get("name")
                or ""
            )
            if not upstream_id:
                raise UpstreamSchemaError("NHC storm identity is missing")
            records.append(
                CanonicalRecord(
                    id=stable_id(self.source_id, upstream_id),
                    source_id=self.source_id,
                    source_name=self.source_name,
                    source_type=SourceType.OFFICIAL_FEED,
                    authority_level=AuthorityLevel.AUTHORITATIVE,
                    source_record_id=upstream_id,
                    source_url=self.url,
                    title=compact_text(
                        storm.get("name")
                        or storm.get("stormName")
                        or storm.get("headline")
                        or "Current tropical system"
                    ),
                    category=self.category,
                    observed_at=parse_datetime(
                        storm.get("lastUpdate") or storm.get("lastUpdateTime")
                    ),
                    published_at=None,
                    retrieved_at=retrieved,
                    expires_at=None,
                    stale=False,
                    stale_reason=None,
                    confidence=1,
                    geography={},
                    zip_scope=[],
                    raw_snapshot_hash=snapshot_hash,
                    schema_version=1,
                    payload={
                        **storm,
                        "gis_products_base": "https://www.nhc.noaa.gov/gis/",
                        "display_only_when_active": True,
                    },
                )
            )
        return records
