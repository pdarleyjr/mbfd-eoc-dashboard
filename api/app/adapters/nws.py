from typing import Any

import httpx

from app.errors import UpstreamSchemaError
from app.schemas import AuthorityLevel, CanonicalRecord, SourceType

from .base import Adapter, FetchedPayload
from .utils import compact_text, parse_datetime, stable_id, utc_now


class NwsAlertsAdapter(Adapter):
    source_id = "nws-alerts"
    source_name = "National Weather Service"
    source_type = SourceType.OFFICIAL_API.value
    authority_level = AuthorityLevel.AUTHORITATIVE.value
    category = "weather_alert"
    url = "https://api.weather.gov/alerts/active?point=25.7907,-80.1300"
    poll_interval_seconds = 45
    stale_threshold_seconds = 120

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
            raise UpstreamSchemaError("NWS alerts response is not a GeoJSON feature collection")
        retrieved = utc_now()
        records: list[CanonicalRecord] = []
        for feature in payload["features"]:
            properties = feature.get("properties") if isinstance(feature, dict) else None
            if not isinstance(properties, dict):
                raise UpstreamSchemaError("NWS alert feature properties are missing")
            upstream_id = str(properties.get("id") or feature.get("id") or "")
            if not upstream_id:
                raise UpstreamSchemaError("NWS alert identity is missing")
            records.append(
                CanonicalRecord(
                    id=stable_id(self.source_id, upstream_id),
                    source_id=self.source_id,
                    source_name=self.source_name,
                    source_type=SourceType.OFFICIAL_API,
                    authority_level=AuthorityLevel.AUTHORITATIVE,
                    source_record_id=upstream_id,
                    source_url=str(feature.get("id") or self.url),
                    title=compact_text(properties.get("headline") or properties.get("event")),
                    category=self.category,
                    observed_at=parse_datetime(properties.get("effective")),
                    published_at=parse_datetime(properties.get("sent")),
                    retrieved_at=retrieved,
                    expires_at=parse_datetime(properties.get("expires")),
                    stale=False,
                    stale_reason=None,
                    confidence=1,
                    geography=feature.get("geometry") or {},
                    zip_scope=["33139", "33140"],
                    raw_snapshot_hash=snapshot_hash,
                    schema_version=1,
                    payload={
                        key: properties.get(key)
                        for key in (
                            "event",
                            "severity",
                            "certainty",
                            "urgency",
                            "areaDesc",
                            "description",
                            "instruction",
                            "status",
                            "messageType",
                        )
                    },
                )
            )
        return records


class NwsForecastAdapter(Adapter):
    source_name = "National Weather Service"
    source_type = SourceType.OFFICIAL_API.value
    authority_level = AuthorityLevel.AUTHORITATIVE.value
    category = "forecast"
    point_url = "https://api.weather.gov/points/25.7907,-80.1300"
    poll_interval_seconds = 300
    stale_threshold_seconds = 900
    retire_missing = True

    def __init__(self, hourly: bool = False) -> None:
        self.hourly = hourly
        self.source_id = "nws-hourly" if hourly else "nws-forecast"
        self.url = self.point_url

    async def fetch(self, client: httpx.AsyncClient) -> FetchedPayload:
        point = await client.get(self.point_url, timeout=self.timeout_seconds)
        point.raise_for_status()
        properties = point.json().get("properties", {})
        forecast_url = properties.get("forecastHourly" if self.hourly else "forecast")
        if not forecast_url:
            raise UpstreamSchemaError("NWS point metadata did not provide a forecast URL")
        response = await client.get(forecast_url, timeout=self.timeout_seconds)
        response.raise_for_status()
        return FetchedPayload(
            body=response.content,
            content_type=response.headers.get("content-type", "application/geo+json"),
            parsed=response.json(),
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        periods = (
            payload.get("properties", {}).get("periods") if isinstance(payload, dict) else None
        )
        if not isinstance(periods, list):
            raise UpstreamSchemaError("NWS forecast periods are missing")
        retrieved = utc_now()
        records: list[CanonicalRecord] = []
        for period in periods:
            if not isinstance(period, dict) or period.get("number") is None:
                raise UpstreamSchemaError("NWS forecast period identity is missing")
            upstream_id = f"{period['number']}:{period.get('startTime', '')}"
            records.append(
                CanonicalRecord(
                    id=stable_id(self.source_id, upstream_id),
                    source_id=self.source_id,
                    source_name=self.source_name,
                    source_type=SourceType.OFFICIAL_API,
                    authority_level=AuthorityLevel.AUTHORITATIVE,
                    source_record_id=upstream_id,
                    source_url=self.point_url,
                    title=compact_text(period.get("name") or "Forecast period"),
                    category=self.category,
                    observed_at=parse_datetime(period.get("startTime")),
                    published_at=parse_datetime(payload.get("properties", {}).get("generatedAt")),
                    retrieved_at=retrieved,
                    expires_at=parse_datetime(period.get("endTime")),
                    stale=False,
                    stale_reason=None,
                    confidence=1,
                    geography={},
                    zip_scope=["33139", "33140"],
                    raw_snapshot_hash=snapshot_hash,
                    schema_version=1,
                    payload={**period, "forecast_kind": "hourly" if self.hourly else "period"},
                )
            )
        return records
