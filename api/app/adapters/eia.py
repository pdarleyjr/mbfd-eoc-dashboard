import json
import math
from datetime import UTC, datetime
from typing import Any, cast

import httpx
from dateutil.parser import isoparse

from app.config import get_settings
from app.errors import UpstreamSchemaError
from app.schemas import AuthorityLevel, CanonicalRecord, SourceType

from .base import Adapter, FetchedPayload
from .utils import stable_id, utc_now

EIA_REGION_DATA_ENDPOINT = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
EIA_GRID_MONITOR_URL = "https://www.eia.gov/electricity/gridmonitor/"
FPL_RESPONDENT_NAME = "Florida Power & Light Co."
FPL_SCOPE = "Florida Power & Light balancing authority"
FPL_SCOPE_NOTE = "Regional grid indicator; not a Miami Beach customer-outage count"

METRICS: dict[str, tuple[str, str, str]] = {
    "D": ("demand", "FPL regional grid demand", "Demand"),
    "DF": (
        "day-ahead-demand-forecast",
        "FPL day-ahead demand forecast",
        "Day-ahead demand forecast",
    ),
    "NG": ("net-generation", "FPL regional net generation", "Net generation"),
}


def _without_api_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_api_keys(item)
            for key, item in value.items()
            if str(key).casefold() != "api_key"
        }
    if isinstance(value, list):
        return [_without_api_keys(item) for item in value]
    return value


def _period_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = isoparse(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        # The local-hourly dataset uses the FPL balancing authority's local
        # clock. A missing offset is therefore Eastern time, not UTC.
        from zoneinfo import ZoneInfo

        parsed = parsed.replace(tzinfo=ZoneInfo("America/New_York"))
    return parsed.astimezone(UTC)


class EiaRegionDataAdapter(Adapter):
    source_type = SourceType.OFFICIAL_API.value
    authority_level = AuthorityLevel.AUTHORITATIVE.value
    category = "power_grid_status"
    poll_interval_seconds = 900
    stale_threshold_seconds = 7200
    timeout_seconds = 20
    geographic_filter = f"{FPL_SCOPE}; regional indicator, not municipal outage data"

    def __init__(self, metric_type: str, *, api_key: str | None = None) -> None:
        if metric_type not in METRICS:
            raise ValueError(f"Unsupported EIA region-data metric: {metric_type}")
        slug, title, fallback_name = METRICS[metric_type]
        self.metric_type = metric_type
        self.title = title
        self.fallback_name = fallback_name
        self.source_id = f"eia-fpl-{slug}"
        self.source_name = f"U.S. EIA-930 — FPL {fallback_name}"
        self.url = EIA_REGION_DATA_ENDPOINT
        self._api_key = (
            api_key if api_key is not None else get_settings().eia_api_key.get_secret_value()
        )

    async def fetch(self, client: httpx.AsyncClient) -> FetchedPayload:
        if not self._api_key:
            raise UpstreamSchemaError("EIA API key is not configured")
        response = await client.get(
            self.url,
            params={
                "api_key": self._api_key,
                "frequency": "local-hourly",
                "data[0]": "value",
                "facets[respondent][]": "FPL",
                "facets[type][]": self.metric_type,
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "offset": "0",
                "length": "1",
            },
            headers={"Accept": "application/json"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        parsed = _without_api_keys(response.json())
        body = json.dumps(parsed, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return FetchedPayload(
            body=body,
            content_type="application/json",
            parsed=parsed,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        response = payload.get("response") if isinstance(payload, dict) else None
        rows = response.get("data") if isinstance(response, dict) else None
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            raise UpstreamSchemaError("EIA region-data response has no current row")
        response_data = cast(dict[str, Any], response)
        row = cast(dict[str, Any], rows[0])
        if row.get("respondent") != "FPL" or row.get("type") != self.metric_type:
            raise UpstreamSchemaError("EIA region-data response does not match the FPL metric")
        period = row.get("period")
        observed = _period_time(period)
        if observed is None:
            raise UpstreamSchemaError("EIA region-data period is invalid")
        try:
            numeric_value = float(row["value"])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise UpstreamSchemaError("EIA region-data value is not numeric") from exc
        if not math.isfinite(numeric_value):
            raise UpstreamSchemaError("EIA region-data value is not finite")
        value: int | float = int(numeric_value) if numeric_value.is_integer() else numeric_value
        unit = row.get("value-units")
        if not isinstance(unit, str) or not unit.strip():
            raise UpstreamSchemaError("EIA region-data unit is missing")
        respondent_name = row.get("respondent-name")
        metric_name = row.get("type-name")
        frequency = response_data.get("frequency")
        retrieved = utc_now()
        source_record_id = f"FPL:{self.metric_type}:{period}"
        return [
            CanonicalRecord(
                id=stable_id(self.source_id, source_record_id),
                source_id=self.source_id,
                source_name=self.source_name,
                source_type=SourceType.OFFICIAL_API,
                authority_level=AuthorityLevel.AUTHORITATIVE,
                source_record_id=source_record_id,
                source_url=EIA_GRID_MONITOR_URL,
                title=self.title,
                category=self.category,
                observed_at=observed,
                published_at=observed,
                retrieved_at=retrieved,
                expires_at=None,
                stale=False,
                stale_reason=None,
                confidence=1,
                geography={},
                zip_scope=[],
                raw_snapshot_hash=snapshot_hash,
                schema_version=self.schema_version,
                payload={
                    "respondent": "FPL",
                    "respondent_name": (
                        respondent_name if isinstance(respondent_name, str) else FPL_RESPONDENT_NAME
                    ),
                    "metric_type": self.metric_type,
                    "metric_name": (
                        metric_name if isinstance(metric_name, str) else self.fallback_name
                    ),
                    "value": value,
                    "unit": unit,
                    "period": period,
                    "frequency": frequency if isinstance(frequency, str) else "local-hourly",
                    "geographic_scope": FPL_SCOPE,
                    "scope_note": FPL_SCOPE_NOTE,
                },
            )
        ]
