from typing import Any

from app.config import get_settings
from app.errors import UpstreamSchemaError
from app.schemas import AuthorityLevel, CanonicalRecord, SourceType

from .base import Adapter
from .utils import parse_datetime, stable_id, utc_now


class PulsePointAdapter(Adapter):
    source_id = "pulsepoint-x1012"
    source_name = "PulsePoint Miami Beach X1012"
    source_type = SourceType.PULSEPOINT_ADVISORY.value
    authority_level = AuthorityLevel.ADVISORY.value
    category = "pulsepoint_call"
    poll_interval_seconds = 15
    stale_threshold_seconds = 90
    timeout_seconds = 12
    retire_missing = False

    def __init__(self) -> None:
        self.url = str(get_settings().pulsepoint_url)

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        if not isinstance(payload, dict):
            raise UpstreamSchemaError("PulsePoint response must be an object")
        if not isinstance(payload.get("active", []), list) or not isinstance(
            payload.get("recent", []), list
        ):
            raise UpstreamSchemaError("PulsePoint active/recent collections are invalid")
        retrieved = parse_datetime(payload.get("fetchedAt")) or utc_now()
        records: list[CanonicalRecord] = []
        for state in ("active", "recent"):
            for raw in payload.get(state, []):
                if not isinstance(raw, dict) or not raw.get("id"):
                    raise UpstreamSchemaError("PulsePoint incident identity is missing")
                upstream_id = str(raw["id"])
                lat, lng = raw.get("lat"), raw.get("lng")
                geography: dict[str, Any] = {}
                if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                    geography = {"type": "Point", "coordinates": [lng, lat]}
                units = [
                    {
                        "id": str(unit.get("id", "")),
                        "status": unit.get("status"),
                        "cleared_at": unit.get("clearedAt"),
                    }
                    for unit in raw.get("units", [])
                    if isinstance(unit, dict)
                ]
                observed = parse_datetime(raw.get("receivedAt"))
                records.append(
                    CanonicalRecord(
                        id=stable_id(self.source_id, upstream_id),
                        source_id=self.source_id,
                        source_name=self.source_name,
                        source_type=SourceType.PULSEPOINT_ADVISORY,
                        authority_level=AuthorityLevel.ADVISORY,
                        source_record_id=upstream_id,
                        source_url=self.url,
                        title=str(
                            raw.get("callType") or raw.get("callTypeCode") or "Advisory call"
                        ),
                        category=self.category,
                        observed_at=observed,
                        published_at=observed,
                        retrieved_at=retrieved,
                        expires_at=parse_datetime(raw.get("closedAt")),
                        stale=bool(payload.get("stale")),
                        stale_reason="Upstream feed marked stale" if payload.get("stale") else None,
                        confidence=1,
                        geography=geography,
                        zip_scope=[],
                        raw_snapshot_hash=snapshot_hash,
                        schema_version=1,
                        payload={
                            "state": state,
                            "call_type_code": raw.get("callTypeCode"),
                            "address": str(raw.get("address", "")),
                            "units": units,
                            "agency": str(payload.get("agency") or "X1012"),
                            "disclaimer": "PulsePoint advisory feed — not official CAD",
                        },
                    )
                )
        return records
