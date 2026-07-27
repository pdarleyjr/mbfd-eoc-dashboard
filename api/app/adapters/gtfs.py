import csv
import io
import zipfile
from collections import defaultdict
from typing import Any

import httpx

from app.errors import UpstreamSchemaError
from app.geography import is_miami_beach_relevant
from app.schemas import AuthorityLevel, CanonicalRecord, SourceType

from .base import Adapter, FetchedPayload
from .utils import compact_text, stable_id, utc_now


class MiamiDadeGtfsAdapter(Adapter):
    source_id = "miami-dade-static-gtfs"
    source_name = "Miami-Dade Transit Static GTFS"
    source_type = SourceType.OFFICIAL_FEED.value
    authority_level = AuthorityLevel.AUTHORITATIVE.value
    category = "transit"
    url = "https://www.miamidade.gov/transit/googletransit/current/google_transit.zip"
    poll_interval_seconds = 21600
    stale_threshold_seconds = 43200
    timeout_seconds = 45
    retire_missing = True

    async def fetch(self, client: httpx.AsyncClient) -> FetchedPayload:
        response = await client.get(
            self.url,
            headers={"Accept": "application/zip,application/octet-stream;q=0.9,*/*;q=0.1"},
            timeout=self.timeout_seconds,
            follow_redirects=True,
        )
        response.raise_for_status()
        return FetchedPayload(
            body=response.content,
            content_type=response.headers.get("content-type", "application/zip"),
            parsed=response.content,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        if not isinstance(payload, bytes):
            raise UpstreamSchemaError("GTFS response is not a ZIP archive")
        try:
            archive = zipfile.ZipFile(io.BytesIO(payload))
            stops = self._read_csv(archive, "stops.txt")
            routes = self._read_csv(archive, "routes.txt")
            trips = self._read_csv(archive, "trips.txt")
            stop_times = self._read_csv(archive, "stop_times.txt")
            shapes = (
                self._read_csv(archive, "shapes.txt") if "shapes.txt" in archive.namelist() else []
            )
        except (KeyError, zipfile.BadZipFile, UnicodeError) as exc:
            raise UpstreamSchemaError(
                "GTFS archive is malformed or missing required tables"
            ) from exc

        relevant_stops: dict[str, dict[str, str]] = {}
        for stop in stops:
            try:
                lat, lon = float(stop["stop_lat"]), float(stop["stop_lon"])
            except (KeyError, TypeError, ValueError):
                continue
            if is_miami_beach_relevant(lon, lat):
                relevant_stops[stop["stop_id"]] = stop

        relevant_trip_ids = {
            row.get("trip_id", "") for row in stop_times if row.get("stop_id") in relevant_stops
        }
        relevant_trips = {
            row.get("trip_id", ""): row for row in trips if row.get("trip_id") in relevant_trip_ids
        }
        relevant_route_ids = {
            row.get("route_id", "") for row in relevant_trips.values() if row.get("route_id")
        }
        route_lookup = {row.get("route_id", ""): row for row in routes}
        route_shapes: dict[str, set[str]] = defaultdict(set)
        for trip in relevant_trips.values():
            if trip.get("shape_id"):
                route_shapes[trip.get("route_id", "")].add(trip["shape_id"])
        relevant_shape_ids = set().union(*route_shapes.values()) if route_shapes else set()
        shape_points: dict[str, list[tuple[int, list[float]]]] = defaultdict(list)
        for row in shapes:
            if row.get("shape_id") not in relevant_shape_ids:
                continue
            try:
                shape_points[row["shape_id"]].append(
                    (
                        int(row.get("shape_pt_sequence", "0")),
                        [float(row["shape_pt_lon"]), float(row["shape_pt_lat"])],
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue

        retrieved = utc_now()
        records: list[CanonicalRecord] = []
        for stop_id, stop in relevant_stops.items():
            lon, lat = float(stop["stop_lon"]), float(stop["stop_lat"])
            records.append(
                CanonicalRecord(
                    id=stable_id(self.source_id, f"stop:{stop_id}"),
                    source_id=self.source_id,
                    source_name=self.source_name,
                    source_type=SourceType.OFFICIAL_FEED,
                    authority_level=AuthorityLevel.AUTHORITATIVE,
                    source_record_id=f"stop:{stop_id}",
                    source_url=self.url,
                    title=compact_text(stop.get("stop_name") or f"Transit stop {stop_id}"),
                    category=self.category,
                    observed_at=None,
                    published_at=None,
                    retrieved_at=retrieved,
                    expires_at=None,
                    stale=False,
                    stale_reason=None,
                    confidence=1,
                    geography={"type": "Point", "coordinates": [lon, lat]},
                    zip_scope=[],
                    raw_snapshot_hash=snapshot_hash,
                    schema_version=1,
                    payload={
                        "record_kind": "stop",
                        "stop_id": stop_id,
                        "stop_code": stop.get("stop_code"),
                        "wheelchair_boarding": stop.get("wheelchair_boarding"),
                        "schedule_only": True,
                    },
                )
            )
        for route_id in sorted(relevant_route_ids):
            route = route_lookup.get(route_id, {})
            coordinates: list[list[float]] = []
            for shape_id in sorted(route_shapes.get(route_id, set()))[:1]:
                coordinates = [point for _, point in sorted(shape_points.get(shape_id, []))]
            records.append(
                CanonicalRecord(
                    id=stable_id(self.source_id, f"route:{route_id}"),
                    source_id=self.source_id,
                    source_name=self.source_name,
                    source_type=SourceType.OFFICIAL_FEED,
                    authority_level=AuthorityLevel.AUTHORITATIVE,
                    source_record_id=f"route:{route_id}",
                    source_url=self.url,
                    title=compact_text(
                        route.get("route_long_name")
                        or route.get("route_short_name")
                        or f"Transit route {route_id}"
                    ),
                    category=self.category,
                    observed_at=None,
                    published_at=None,
                    retrieved_at=retrieved,
                    expires_at=None,
                    stale=False,
                    stale_reason=None,
                    confidence=1,
                    geography=(
                        {"type": "LineString", "coordinates": coordinates} if coordinates else {}
                    ),
                    zip_scope=[],
                    raw_snapshot_hash=snapshot_hash,
                    schema_version=1,
                    payload={
                        "record_kind": "route",
                        "route_id": route_id,
                        "route_short_name": route.get("route_short_name"),
                        "route_type": route.get("route_type"),
                        "route_color": route.get("route_color"),
                        "schedule_only": True,
                        "no_realtime_vehicle_data": True,
                    },
                )
            )
        return records

    @staticmethod
    def _read_csv(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
        with archive.open(name) as handle:
            text = io.TextIOWrapper(handle, encoding="utf-8-sig", newline="")
            return list(csv.DictReader(text))
