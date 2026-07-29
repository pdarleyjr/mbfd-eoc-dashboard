from datetime import timedelta
from itertools import pairwise
from statistics import median
from typing import Any
from xml.etree.ElementTree import Element, ParseError

import httpx
from defusedxml import ElementTree

from app.errors import UpstreamSchemaError
from app.schemas import AuthorityLevel, CanonicalRecord, SourceType

from .base import Adapter, FetchedPayload
from .utils import parse_datetime, stable_id, utc_now

RADAR_WMS_URL = "https://nowcoast.noaa.gov/geoserver/observations/weather_radar/wms"
RADAR_CAPABILITIES_URL = f"{RADAR_WMS_URL}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"
RADAR_LAYER_NAME = "conus_base_reflectivity_mosaic"
RADAR_LEGEND_URL = (
    "https://nowcoast.noaa.gov/geoserver/observations/weather_radar/ows"
    "?service=WMS&version=1.3.0&request=GetLegendGraphic&format=image%2Fpng"
    f"&width=272&height=21&layer={RADAR_LAYER_NAME}"
)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class NoaaRadarStatusAdapter(Adapter):
    source_id = "noaa-mrms-radar-status"
    source_name = "NOAA nowCOAST MRMS Radar"
    source_type = SourceType.OFFICIAL_GIS.value
    authority_level = AuthorityLevel.AUTHORITATIVE.value
    category = "radar_status"
    url = RADAR_CAPABILITIES_URL
    poll_interval_seconds = 300
    stale_threshold_seconds = 900
    schema_version = 1
    retire_missing = True

    async def fetch(self, client: httpx.AsyncClient) -> FetchedPayload:
        response = await client.get(
            self.url,
            headers={"Accept": "application/xml,text/xml"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return FetchedPayload(
            body=response.content,
            content_type=response.headers.get("content-type", "application/xml"),
            parsed=response.text,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

    def normalize(self, payload: Any, snapshot_hash: str) -> list[CanonicalRecord]:
        if not isinstance(payload, str):
            raise UpstreamSchemaError("NOAA radar capabilities response is not XML text")
        try:
            root = ElementTree.fromstring(payload)
        except ParseError as exc:
            raise UpstreamSchemaError("NOAA radar capabilities XML is invalid") from exc

        radar_layer: Element | None = None
        for layer in (element for element in root.iter() if _local_name(element.tag) == "Layer"):
            name = next(
                (
                    child.text.strip()
                    for child in layer
                    if _local_name(child.tag) == "Name" and child.text
                ),
                None,
            )
            if name == RADAR_LAYER_NAME:
                radar_layer = layer
                break
        if radar_layer is None:
            raise UpstreamSchemaError("NOAA radar capabilities omitted the CONUS MRMS layer")

        dimension = next(
            (
                element
                for element in radar_layer
                if _local_name(element.tag) == "Dimension"
                and element.attrib.get("name", "").lower() == "time"
            ),
            None,
        )
        if dimension is None or not dimension.text:
            raise UpstreamSchemaError("NOAA radar layer omitted its service-reported time extent")

        parsed_frames = [parse_datetime(value.strip()) for value in dimension.text.split(",")]
        if any(frame is None for frame in parsed_frames):
            raise UpstreamSchemaError("NOAA radar layer returned an invalid frame timestamp")
        frames = sorted({frame for frame in parsed_frames if frame is not None})
        if not frames:
            raise UpstreamSchemaError("NOAA radar layer returned no available frames")

        default_frame = parse_datetime(dimension.attrib.get("default"))
        latest = max(frames)
        if default_frame is not None and default_frame > latest:
            latest = default_frame
            frames.append(default_frame)
            frames.sort()

        intervals = [
            int((current - previous).total_seconds())
            for previous, current in pairwise(frames)
            if current > previous
        ]
        update_frequency = max(60, int(round(median(intervals) / 60) * 60)) if intervals else 240
        retrieved = utc_now()
        delayed = retrieved - latest > timedelta(
            seconds=max(self.stale_threshold_seconds, update_frequency * 3)
        )

        legend_url = RADAR_LEGEND_URL
        for element in radar_layer.iter():
            if _local_name(element.tag) != "OnlineResource":
                continue
            href = next(
                (value for key, value in element.attrib.items() if _local_name(key) == "href"),
                None,
            )
            if href and "GetLegendGraphic" in href:
                legend_url = href
                break

        return [
            CanonicalRecord(
                id=stable_id(self.source_id, RADAR_LAYER_NAME),
                source_id=self.source_id,
                source_name=self.source_name,
                source_type=SourceType.OFFICIAL_GIS,
                authority_level=AuthorityLevel.AUTHORITATIVE,
                source_record_id=RADAR_LAYER_NAME,
                source_url=self.url,
                title="NOAA MRMS base reflectivity status",
                category=self.category,
                observed_at=latest,
                published_at=None,
                retrieved_at=retrieved,
                expires_at=None,
                stale=delayed,
                stale_reason=(
                    f"Radar delayed; last service-reported frame was {latest.isoformat()}"
                    if delayed
                    else None
                ),
                confidence=1,
                geography={},
                zip_scope=["33139", "33140"],
                raw_snapshot_hash=snapshot_hash,
                schema_version=self.schema_version,
                payload={
                    "service_available": True,
                    "latest_frame_time": latest.isoformat(),
                    "extent_start": frames[0].isoformat(),
                    "extent_end": frames[-1].isoformat(),
                    "frame_times": [frame.isoformat() for frame in frames],
                    "retrieved_at": retrieved.isoformat(),
                    "update_frequency_seconds": update_frequency,
                    "service_url": RADAR_WMS_URL,
                    "capabilities_url": self.url,
                    "layer_name": RADAR_LAYER_NAME,
                    "legend_url": legend_url,
                    "schema_version": self.schema_version,
                },
            )
        ]
