from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Any
from urllib.parse import urlencode

from shapely import make_valid
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union

from app.errors import UpstreamSchemaError
from app.geography import is_miami_beach_relevant
from app.schemas import AuthorityLevel, CanonicalRecord, SourceType

from .base import Adapter
from .utils import compact_text, json_safe, parse_datetime, stable_id, utc_now


@dataclass(frozen=True)
class ArcGisSource:
    source_id: str
    source_name: str
    url: str
    category: str
    title_field: str
    id_field: str = "OBJECTID"
    observed_field: str | None = None
    expires_field: str | None = None
    where: str = "1=1"
    poll_interval_seconds: int = 300
    stale_threshold_seconds: int = 900
    authority_level: AuthorityLevel = AuthorityLevel.AUTHORITATIVE
    geographic_scope: bool = True
    zip_fields: tuple[str, ...] = ("ZIP", "ZIPCODE", "Zipcode", "POSTAL")
    fixed_title: str | None = None
    include_fields: tuple[str, ...] = ()
    timeout_seconds: float = 45


class ArcGisAdapter(Adapter):
    source_type = SourceType.OFFICIAL_GIS.value
    schema_version = 1

    def __init__(self, source: ArcGisSource) -> None:
        self.source = source
        self.source_id = source.source_id
        self.source_name = source.source_name
        fields = list(
            dict.fromkeys(
                field
                for field in (
                    source.id_field,
                    source.title_field,
                    source.observed_field,
                    source.expires_field,
                    *source.include_fields,
                )
                if field
            )
        )
        query: dict[str, str] = {
            "where": source.where,
            "outFields": ",".join(fields),
            "returnGeometry": "true",
            "returnTrueCurves": "false",
            "outSR": "4326",
            "geometryPrecision": "6",
            "f": "json",
        }
        if source.geographic_scope:
            query.update(
                {
                    "geometry": "-80.20,25.74,-80.10,25.89",
                    "geometryType": "esriGeometryEnvelope",
                    "inSR": "4326",
                    "spatialRel": "esriSpatialRelIntersects",
                }
            )
        self.url = f"{source.url.rstrip('/')}/query?{urlencode(query)}"
        self.category = source.category
        self.authority_level = source.authority_level.value
        self.poll_interval_seconds = source.poll_interval_seconds
        self.stale_threshold_seconds = source.stale_threshold_seconds
        self.timeout_seconds = source.timeout_seconds
        self.retire_missing = True
        self.geographic_filter = (
            "PostGIS/local Miami Beach operational scope"
            if source.geographic_scope
            else "Source query returns the configured Miami-Dade summary"
        )

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        if not isinstance(payload, dict) or payload.get("error"):
            raise UpstreamSchemaError("ArcGIS returned an error response")
        features = payload.get("features")
        if not isinstance(features, list):
            raise UpstreamSchemaError("ArcGIS response is missing features")
        retrieved = utc_now()
        records: list[CanonicalRecord] = []
        for feature in features:
            if not isinstance(feature, dict) or not isinstance(feature.get("attributes"), dict):
                raise UpstreamSchemaError("ArcGIS feature attributes are invalid")
            attributes = feature["attributes"]
            object_id = attributes.get(self.source.id_field)
            if object_id is None:
                object_id = attributes.get("OBJECTID") or attributes.get("FID")
            if object_id is None:
                raise UpstreamSchemaError("ArcGIS feature identity is missing")
            geography = self._geometry(feature.get("geometry"))
            if self.source.geographic_scope and geography.get("type") == "Point":
                longitude, latitude = geography["coordinates"]
                zip_match = any(
                    str(attributes.get(field, "")).strip() in {"33139", "33140"}
                    for field in self.source.zip_fields
                )
                if not zip_match and not is_miami_beach_relevant(longitude, latitude):
                    continue
            source_record_id = str(object_id)
            title = self.source.fixed_title or compact_text(
                attributes.get(self.source.title_field)
                or attributes.get("NAME")
                or attributes.get("Name")
                or f"{self.source.source_name} record {object_id}"
            )
            observed = (
                parse_datetime(attributes.get(self.source.observed_field))
                if self.source.observed_field
                else None
            )
            expires = (
                parse_datetime(attributes.get(self.source.expires_field))
                if self.source.expires_field
                else None
            )
            normalized_attributes = (
                {
                    field: attributes.get(field)
                    for field in self.source.include_fields
                    if field in attributes
                }
                if self.source.include_fields
                else attributes
            )
            if geography.get("type") == "Point":
                longitude, latitude = geography["coordinates"]
                normalized_attributes = {
                    **normalized_attributes,
                    "distance_from_miami_beach_miles": round(
                        self._distance_miles(latitude, longitude, 25.7907, -80.1300), 1
                    ),
                }
            records.append(
                CanonicalRecord(
                    id=stable_id(self.source_id, source_record_id),
                    source_id=self.source_id,
                    source_name=self.source_name,
                    source_type=SourceType.OFFICIAL_GIS,
                    authority_level=self.source.authority_level,
                    source_record_id=source_record_id,
                    source_url=self.source.url,
                    title=title,
                    category=self.category,
                    observed_at=observed,
                    published_at=None,
                    retrieved_at=retrieved,
                    expires_at=expires,
                    stale=False,
                    stale_reason=None,
                    confidence=1,
                    geography=geography,
                    zip_scope=[
                        value
                        for field in self.source.zip_fields
                        if (value := str(attributes.get(field, "")).strip()) in {"33139", "33140"}
                    ],
                    raw_snapshot_hash=snapshot_hash,
                    schema_version=1,
                    payload=json_safe(normalized_attributes),
                )
            )
        return records

    @staticmethod
    def _geometry(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        if isinstance(value.get("x"), (int, float)) and isinstance(value.get("y"), (int, float)):
            return {"type": "Point", "coordinates": [value["x"], value["y"]]}
        if isinstance(value.get("paths"), list):
            paths = value["paths"]
            return {
                "type": "LineString" if len(paths) == 1 else "MultiLineString",
                "coordinates": paths[0] if len(paths) == 1 else paths,
            }
        if isinstance(value.get("rings"), list):
            polygon = shape({"type": "Polygon", "coordinates": value["rings"]})
            if not polygon.is_valid:
                polygon = make_valid(polygon)
            if isinstance(polygon, GeometryCollection):
                polygonal = [
                    geometry
                    for geometry in polygon.geoms
                    if isinstance(geometry, (Polygon, MultiPolygon))
                ]
                if not polygonal:
                    raise UpstreamSchemaError("ArcGIS polygon contains no usable area")
                polygon = unary_union(polygonal)
            normalized = json_safe(mapping(polygon))
            if not isinstance(normalized, dict):
                raise UpstreamSchemaError("ArcGIS polygon normalization failed")
            return normalized
        return {}

    @staticmethod
    def _distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius_miles = 3958.8
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        return 2 * radius_miles * asin(sqrt(a))
