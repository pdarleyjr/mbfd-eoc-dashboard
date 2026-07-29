import json
from datetime import timedelta
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


class NwsObservationAdapter(Adapter):
    source_id = "nws-observation"
    source_name = "National Weather Service Observation"
    source_type = SourceType.OFFICIAL_API.value
    authority_level = AuthorityLevel.AUTHORITATIVE.value
    category = "weather_observation"
    point_url = "https://api.weather.gov/points/25.7907,-80.1300"
    url = point_url
    poll_interval_seconds = 300
    stale_threshold_seconds = 900
    retire_missing = True

    async def fetch(self, client: httpx.AsyncClient) -> FetchedPayload:
        point_response = await client.get(self.point_url, timeout=self.timeout_seconds)
        point_response.raise_for_status()
        point_payload = point_response.json()
        station_collection_url = point_payload.get("properties", {}).get("observationStations")
        if not isinstance(station_collection_url, str) or not station_collection_url:
            raise UpstreamSchemaError("NWS point metadata omitted observation stations")

        stations_response = await client.get(station_collection_url, timeout=self.timeout_seconds)
        stations_response.raise_for_status()
        features = stations_response.json().get("features")
        if not isinstance(features, list) or not features:
            raise UpstreamSchemaError("NWS returned no observation stations for Miami Beach")
        station_feature = features[0]
        if not isinstance(station_feature, dict):
            raise UpstreamSchemaError("NWS observation station metadata is invalid")
        station_properties = station_feature.get("properties")
        if not isinstance(station_properties, dict):
            raise UpstreamSchemaError("NWS observation station properties are invalid")
        station_url = station_feature.get("id")
        if not isinstance(station_url, str) or not station_url:
            raise UpstreamSchemaError("NWS observation station URL is missing")

        observation_url = f"{station_url.rstrip('/')}/observations/latest?require_qc=true"
        observation_response = await client.get(observation_url, timeout=self.timeout_seconds)
        observation_response.raise_for_status()
        observation_payload = observation_response.json()
        properties = observation_payload.get("properties")
        if not isinstance(properties, dict):
            raise UpstreamSchemaError("NWS latest observation properties are invalid")

        parsed = {
            "station": {
                "id": station_properties.get("stationIdentifier"),
                "name": station_properties.get("name"),
                "url": station_url,
                "geometry": station_feature.get("geometry") or {},
            },
            "observation": properties,
            "observation_url": observation_url,
        }
        body = json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode()
        return FetchedPayload(
            body=body,
            content_type="application/geo+json",
            parsed=parsed,
            etag=observation_response.headers.get("etag"),
            last_modified=observation_response.headers.get("last-modified"),
        )

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        if not isinstance(payload, dict):
            raise UpstreamSchemaError("NWS observation response is not an object")
        station = payload.get("station")
        observation = payload.get("observation")
        if not isinstance(station, dict) or not isinstance(observation, dict):
            raise UpstreamSchemaError("NWS observation response omitted station or measurement")
        station_id = str(station.get("id") or "").strip()
        station_name = compact_text(station.get("name") or station_id)
        observed = parse_datetime(observation.get("timestamp"))
        if not station_id or observed is None:
            raise UpstreamSchemaError("NWS observation identity or timestamp is missing")

        measurement_fields = (
            "temperature",
            "relativeHumidity",
            "windDirection",
            "windSpeed",
            "windGust",
            "visibility",
            "barometricPressure",
            "precipitationLastHour",
        )
        measurements = {
            field: observation.get(field)
            for field in measurement_fields
            if isinstance(observation.get(field), dict)
        }
        retrieved = utc_now()
        return [
            CanonicalRecord(
                id=stable_id(self.source_id, f"{station_id}:{observed.isoformat()}"),
                source_id=self.source_id,
                source_name=self.source_name,
                source_type=SourceType.OFFICIAL_API,
                authority_level=AuthorityLevel.AUTHORITATIVE,
                source_record_id=f"{station_id}:{observed.isoformat()}",
                source_url=str(payload.get("observation_url") or station.get("url") or self.url),
                title=f"Observed conditions at {station_name}",
                category=self.category,
                observed_at=observed,
                published_at=None,
                retrieved_at=retrieved,
                expires_at=observed + timedelta(minutes=30),
                stale=False,
                stale_reason=None,
                confidence=1,
                geography=station.get("geometry") or {},
                zip_scope=["33139", "33140"],
                raw_snapshot_hash=snapshot_hash,
                schema_version=1,
                payload={
                    "station_id": station_id,
                    "station_name": station_name,
                    **measurements,
                },
            )
        ]
