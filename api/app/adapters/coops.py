from datetime import timedelta
from typing import Any

from app.errors import UpstreamSchemaError
from app.schemas import AuthorityLevel, CanonicalRecord, SourceType

from .base import Adapter
from .utils import parse_datetime, stable_id, utc_now

PRODUCT_LABELS = {
    "water_level": "Observed water level",
    "predictions": "Predicted tide",
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
        self.source_id = f"coops-{product.replace('_', '-')}"
        self.poll_interval_seconds = 21600 if product == "predictions" else 330
        interval = "hilo" if product == "predictions" else "6"
        datum = "&datum=MLLW" if product in {"water_level", "predictions"} else ""
        date = "today" if product == "predictions" else "latest"
        self.url = (
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
            f"?product={product}&application=MBFD_EOC&date={date}{datum}"
            f"&station=8723214&time_zone=gmt&units=metric&interval={interval}&format=json"
        )

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        if not isinstance(payload, dict) or payload.get("error"):
            raise UpstreamSchemaError("CO-OPS returned an error or non-object response")
        rows = payload.get("predictions" if self.product == "predictions" else "data")
        if not isinstance(rows, list):
            raise UpstreamSchemaError("CO-OPS measurement collection is missing")
        retrieved = utc_now()
        kind = "predicted" if self.product == "predictions" else "observed"
        records: list[CanonicalRecord] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise UpstreamSchemaError("CO-OPS measurement row is invalid")
            observed = parse_datetime(row.get("t"))
            if observed is None:
                raise UpstreamSchemaError("CO-OPS measurement time is invalid")
            upstream_id = f"{self.product}:{row.get('t')}:{row.get('ty', index)}"
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
                    expires_at=observed + timedelta(hours=12 if kind == "predicted" else 2),
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
                        "measurement_kind": kind,
                        "units": "metric",
                        "datum": "MLLW" if self.product in {"water_level", "predictions"} else None,
                    },
                )
            )
        return records
