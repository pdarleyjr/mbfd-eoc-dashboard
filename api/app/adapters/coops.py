from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from app.errors import UpstreamSchemaError
from app.schemas import AuthorityLevel, CanonicalRecord, SourceType

from .base import Adapter, FetchedPayload
from .utils import parse_datetime, stable_id, utc_now

PRODUCT_LABELS = {
    "water_level": "Observed water level",
    "predicted_water_level": "Predicted water level",
    "tide_predictions": "Predicted high and low tide",
    "air_temperature": "Air temperature",
    "water_temperature": "Water temperature",
    "wind": "Wind",
    "air_pressure": "Barometric pressure",
}


class CoopsAdapter(Adapter):
    source_name = "NOAA CO-OPS — Virginia Key 8723214"
    source_type = SourceType.OFFICIAL_API.value
    authority_level = AuthorityLevel.AUTHORITATIVE.value
    category = "coastal_observation"
    stale_threshold_seconds = 900
    retire_missing = True

    def __init__(self, product: str) -> None:
        if product not in PRODUCT_LABELS:
            raise ValueError(f"unsupported CO-OPS product: {product}")
        self.product = product
        self.source_product = (
            "predictions" if product in {"predicted_water_level", "tide_predictions"} else product
        )
        self.source_id = f"coops-{product.replace('_', '-')}"
        self.poll_interval_seconds = 21600 if product == "tide_predictions" else 330
        self.endpoint = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        self.url = f"{self.endpoint}?{urlencode(self._query_parameters())}"

    def _query_parameters(self) -> dict[str, str]:
        now = utc_now()
        parameters = {
            "product": self.source_product,
            "application": "MBFD_EOC",
            "station": "8723214",
            "time_zone": "gmt",
            "units": "metric",
            "format": "json",
        }
        if self.product in {"water_level", "predicted_water_level", "tide_predictions"}:
            parameters["datum"] = "MLLW"
        if self.product == "water_level":
            parameters.update(
                {
                    "begin_date": (now - timedelta(hours=1)).strftime("%Y%m%d %H:%M"),
                    "range": "1",
                    "interval": "6",
                }
            )
        elif self.product == "predicted_water_level":
            parameters.update(
                {
                    "begin_date": (now - timedelta(hours=1)).strftime("%Y%m%d %H:%M"),
                    "range": "2",
                    "interval": "6",
                }
            )
        elif self.product == "tide_predictions":
            parameters.update(
                {
                    "begin_date": now.strftime("%Y%m%d"),
                    "range": "48",
                    "interval": "hilo",
                }
            )
        else:
            parameters.update({"date": "latest", "interval": "6"})
        return parameters

    async def fetch(self, client: httpx.AsyncClient) -> FetchedPayload:
        response = await client.get(
            self.endpoint,
            params=self._query_parameters(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return FetchedPayload(
            body=response.content,
            content_type=response.headers.get("content-type", "application/json"),
            parsed=response.json(),
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        if not isinstance(payload, dict) or payload.get("error"):
            raise UpstreamSchemaError("CO-OPS returned an error or non-object response")
        rows = payload.get(
            "predictions"
            if self.product in {"predicted_water_level", "tide_predictions"}
            else "data"
        )
        if not isinstance(rows, list):
            raise UpstreamSchemaError("CO-OPS measurement collection is missing")
        retrieved = utc_now()
        kind = (
            "predicted"
            if self.product in {"predicted_water_level", "tide_predictions"}
            else "observed"
        )
        records: list[CanonicalRecord] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise UpstreamSchemaError("CO-OPS measurement row is invalid")
            observed = parse_datetime(row.get("t"))
            if observed is None:
                raise UpstreamSchemaError("CO-OPS measurement time is invalid")
            tide_type = row.get("type") or row.get("ty")
            upstream_id = f"{self.product}:{row.get('t')}:{tide_type or index}"
            records.append(
                CanonicalRecord(
                    id=stable_id(self.source_id, upstream_id),
                    source_id=self.source_id,
                    source_name=self.source_name,
                    source_type=SourceType.OFFICIAL_API,
                    authority_level=AuthorityLevel.AUTHORITATIVE,
                    source_record_id=upstream_id,
                    source_url=self.url,
                    title=PRODUCT_LABELS[self.product],
                    category=self.category,
                    observed_at=observed,
                    published_at=None,
                    retrieved_at=retrieved,
                    expires_at=observed
                    + timedelta(hours=12 if self.product == "tide_predictions" else 2),
                    stale=False,
                    stale_reason=None,
                    confidence=1,
                    geography={"type": "Point", "coordinates": [-80.1618, 25.7314]},
                    zip_scope=[],
                    raw_snapshot_hash=snapshot_hash,
                    schema_version=1,
                    payload={
                        **row,
                        "station": "8723214",
                        "station_name": "Virginia Key, Biscayne Bay",
                        "product": self.product,
                        "source_product": self.source_product,
                        "measurement_kind": kind,
                        "tide_type": tide_type,
                        "units": "metric",
                        "datum": (
                            "MLLW"
                            if self.product
                            in {"water_level", "predicted_water_level", "tide_predictions"}
                            else None
                        ),
                    },
                )
            )
        return records
