import asyncio
import io
import json
import zipfile
from datetime import datetime
from typing import Any
from xml.etree.ElementTree import Element, ParseError

import httpx
from defusedxml import ElementTree

from app.errors import UpstreamSchemaError
from app.schemas import AuthorityLevel, CanonicalRecord, SourceType

from .base import Adapter, FetchedPayload
from .utils import compact_text, parse_datetime, stable_id, utc_now

MAX_KMZ_BYTES = 5_000_000
GIS_PRODUCTS = {
    "forecastTrack": ("forecast_track", "forecast track"),
    "trackCone": ("forecast_cone", "cone of uncertainty"),
    "windWatchesWarnings": ("watch_warning", "coastal watches and warnings"),
    "initialWindExtent": ("current_wind_radii", "current wind radii"),
    "forecastWindRadiiGIS": ("forecast_wind_radii", "forecast wind radii"),
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _coordinates(text: str | None) -> list[list[float]]:
    if not text:
        return []
    coordinates: list[list[float]] = []
    for token in text.split():
        values = token.strip().split(",")
        if len(values) < 2:
            continue
        try:
            coordinates.append([float(values[0]), float(values[1])])
        except ValueError as exc:
            raise UpstreamSchemaError("NHC GIS product contains invalid coordinates") from exc
    return coordinates


def _first_coordinates(element: Element) -> list[list[float]]:
    for descendant in element.iter():
        if _local_name(descendant.tag) == "coordinates":
            return _coordinates(descendant.text)
    return []


def _kml_geometry(kml: str) -> dict[str, Any]:
    try:
        root = ElementTree.fromstring(kml)
    except ParseError as exc:
        raise UpstreamSchemaError("NHC GIS product contains invalid KML") from exc

    geometries: list[dict[str, Any]] = []
    for element in root.iter():
        kind = _local_name(element.tag)
        if kind == "Point":
            coordinates = _first_coordinates(element)
            if coordinates:
                geometries.append({"type": "Point", "coordinates": coordinates[0]})
        elif kind == "LineString":
            coordinates = _first_coordinates(element)
            if len(coordinates) >= 2:
                geometries.append({"type": "LineString", "coordinates": coordinates})
        elif kind == "Polygon":
            rings: list[list[list[float]]] = []
            for boundary in element:
                boundary_kind = _local_name(boundary.tag)
                if boundary_kind not in {"outerBoundaryIs", "innerBoundaryIs"}:
                    continue
                coordinates = _first_coordinates(boundary)
                if len(coordinates) >= 4:
                    rings.append(coordinates)
            if rings:
                geometries.append({"type": "Polygon", "coordinates": rings})

    if not geometries:
        raise UpstreamSchemaError("NHC GIS product contains no usable geometry")
    if len(geometries) == 1:
        return geometries[0]
    geometry_types = {geometry["type"] for geometry in geometries}
    if geometry_types == {"Point"}:
        return {
            "type": "MultiPoint",
            "coordinates": [geometry["coordinates"] for geometry in geometries],
        }
    if geometry_types == {"LineString"}:
        return {
            "type": "MultiLineString",
            "coordinates": [geometry["coordinates"] for geometry in geometries],
        }
    if geometry_types == {"Polygon"}:
        return {
            "type": "MultiPolygon",
            "coordinates": [geometry["coordinates"] for geometry in geometries],
        }
    return {"type": "GeometryCollection", "geometries": geometries}


def _extract_kml(archive_bytes: bytes) -> str:
    if len(archive_bytes) > MAX_KMZ_BYTES:
        raise UpstreamSchemaError("NHC GIS product exceeds the configured size limit")
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            entries = [
                entry
                for entry in archive.infolist()
                if not entry.is_dir() and entry.filename.lower().endswith(".kml")
            ]
            if len(entries) != 1 or entries[0].file_size > MAX_KMZ_BYTES:
                raise UpstreamSchemaError("NHC GIS archive has an invalid KML payload")
            return archive.read(entries[0]).decode("utf-8")
    except (zipfile.BadZipFile, UnicodeDecodeError) as exc:
        raise UpstreamSchemaError("NHC GIS product is not a valid KMZ archive") from exc


class NhcCurrentStormsAdapter(Adapter):
    source_id = "nhc-current-storms"
    source_name = "National Hurricane Center"
    source_type = SourceType.OFFICIAL_FEED.value
    authority_level = AuthorityLevel.AUTHORITATIVE.value
    category = "tropical"
    url = "https://www.nhc.noaa.gov/CurrentStorms.json"
    poll_interval_seconds = 300
    stale_threshold_seconds = 900

    async def fetch(self, client: httpx.AsyncClient) -> FetchedPayload:
        response = await client.get(self.url, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        storms = payload.get("activeStorms") if isinstance(payload, dict) else None
        if not isinstance(storms, list):
            raise UpstreamSchemaError("NHC activeStorms collection is invalid")

        urls: list[str] = []
        for storm in storms:
            if not isinstance(storm, dict):
                raise UpstreamSchemaError("NHC storm record is invalid")
            for field in GIS_PRODUCTS:
                product = storm.get(field)
                url = product.get("kmzFile") if isinstance(product, dict) else None
                if isinstance(url, str) and url.startswith("https://www.nhc.noaa.gov/"):
                    urls.append(url)

        async def fetch_product(url: str) -> tuple[str, bytes, str]:
            product_response = await client.get(url, timeout=self.timeout_seconds)
            product_response.raise_for_status()
            content = product_response.content
            return url, content, _extract_kml(content)

        fetched_products = await asyncio.gather(
            *(fetch_product(url) for url in dict.fromkeys(urls))
        )
        documents = {url: kml for url, _content, kml in fetched_products}
        parsed = {**payload, "gis_documents": documents}
        body = b"\n".join(
            [
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
                *(content for _url, content, _kml in fetched_products),
            ]
        )
        return FetchedPayload(
            body=body,
            content_type="application/vnd.google-earth.kmz+json",
            parsed=parsed,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        if not isinstance(payload, dict):
            raise UpstreamSchemaError("NHC current storms response must be an object")
        storms = payload.get("activeStorms", [])
        documents = payload.get("gis_documents", {})
        if not isinstance(storms, list):
            raise UpstreamSchemaError("NHC activeStorms collection is invalid")
        if not isinstance(documents, dict):
            raise UpstreamSchemaError("NHC GIS document collection is invalid")
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
            name = compact_text(
                storm.get("name")
                or storm.get("stormName")
                or storm.get("headline")
                or "Current tropical system"
            )
            observed = parse_datetime(storm.get("lastUpdate") or storm.get("lastUpdateTime"))
            longitude = storm.get("longitudeNumeric")
            latitude = storm.get("latitudeNumeric")
            center_geography = (
                {"type": "Point", "coordinates": [float(longitude), float(latitude)]}
                if isinstance(longitude, int | float)
                and not isinstance(longitude, bool)
                and isinstance(latitude, int | float)
                and not isinstance(latitude, bool)
                else {}
            )
            summary = {
                key: storm.get(key)
                for key in (
                    "id",
                    "binNumber",
                    "name",
                    "classification",
                    "intensity",
                    "pressure",
                    "latitude",
                    "longitude",
                    "movementDir",
                    "movementSpeed",
                    "lastUpdate",
                )
                if storm.get(key) is not None
            }
            records.append(
                self._record(
                    upstream_id=upstream_id,
                    name=name,
                    product_kind="center",
                    product_label="active tropical cyclone center",
                    observed=observed,
                    source_url=self.url,
                    geography=center_geography,
                    snapshot_hash=snapshot_hash,
                    retrieved=retrieved,
                    payload=summary,
                )
            )

            for field, (product_kind, product_label) in GIS_PRODUCTS.items():
                product = storm.get(field)
                if not isinstance(product, dict):
                    continue
                product_url = product.get("kmzFile")
                if not isinstance(product_url, str):
                    continue
                kml = documents.get(product_url)
                if not isinstance(kml, str):
                    continue
                product_observed = parse_datetime(
                    product.get("issuance") or product.get("fileUpdateTime")
                )
                records.append(
                    self._record(
                        upstream_id=upstream_id,
                        name=name,
                        product_kind=product_kind,
                        product_label=product_label,
                        observed=product_observed or observed,
                        source_url=product_url,
                        geography=_kml_geometry(kml),
                        snapshot_hash=snapshot_hash,
                        retrieved=retrieved,
                        payload={**summary, **product},
                    )
                )
        return records

    def _record(
        self,
        *,
        upstream_id: str,
        name: str,
        product_kind: str,
        product_label: str,
        observed: datetime | None,
        source_url: str,
        geography: dict[str, Any],
        snapshot_hash: str,
        retrieved: datetime,
        payload: dict[str, Any],
    ) -> CanonicalRecord:
        source_record_id = f"{upstream_id}:{product_kind}"
        return CanonicalRecord(
            id=stable_id(self.source_id, source_record_id),
            source_id=self.source_id,
            source_name=self.source_name,
            source_type=SourceType.OFFICIAL_FEED,
            authority_level=AuthorityLevel.AUTHORITATIVE,
            source_record_id=source_record_id,
            source_url=source_url,
            title=f"{name} — {product_label}",
            category=self.category,
            observed_at=observed,
            published_at=None,
            retrieved_at=retrieved,
            expires_at=None,
            stale=False,
            stale_reason=None,
            confidence=1,
            geography=geography,
            zip_scope=[],
            raw_snapshot_hash=snapshot_hash,
            schema_version=1,
            payload={
                **payload,
                "product_kind": product_kind,
                "display_only_when_active": True,
            },
        )
