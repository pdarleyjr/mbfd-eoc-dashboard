import io
import zipfile

import pytest

from app.adapters.gtfs import MiamiDadeGtfsAdapter
from app.adapters.nhc import NhcCurrentStormsAdapter
from app.adapters.nws import NwsForecastAdapter
from app.errors import UpstreamSchemaError

HASH = "d" * 64


def gtfs_archive() -> bytes:
    files = {
        "stops.txt": (
            "stop_id,stop_name,stop_lat,stop_lon,stop_code,wheelchair_boarding\n"
            "S1,Miami Beach Stop,25.7907,-80.1300,100,1\n"
            "BAD,Bad Coordinates,not-a-number,-80.1,,\n"
        ),
        "routes.txt": (
            "route_id,route_short_name,route_long_name,route_type,route_color\n"
            "R1,100,Miami Beach Route,3,0057B8\n"
        ),
        "trips.txt": "route_id,trip_id,shape_id\nR1,T1,SH1\n",
        "stop_times.txt": (
            "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,12:00:00,12:00:00,S1,1\n"
        ),
        "shapes.txt": (
            "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n"
            "SH1,25.7900,-80.1400,1\n"
            "SH1,25.8000,-80.1200,2\n"
        ),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return buffer.getvalue()


def test_static_gtfs_extracts_only_relevant_stops_and_routes() -> None:
    records = MiamiDadeGtfsAdapter().normalize(gtfs_archive(), HASH)

    assert [item.payload["record_kind"] for item in records] == ["stop", "route"]
    assert records[0].title == "Miami Beach Stop"
    assert records[1].geography["type"] == "LineString"
    assert records[1].payload["schedule_only"] is True
    assert records[1].payload["no_realtime_vehicle_data"] is True


@pytest.mark.parametrize("payload", ["not bytes", b"not a zip"])
def test_static_gtfs_rejects_invalid_archives(payload: object) -> None:
    with pytest.raises(UpstreamSchemaError):
        MiamiDadeGtfsAdapter().normalize(payload, HASH)


def test_nhc_current_storms_normalization_and_empty_state() -> None:
    adapter = NhcCurrentStormsAdapter()
    records = adapter.normalize(
        {
            "activeStorms": [
                {
                    "id": "AL012026",
                    "name": "Alex",
                    "lastUpdate": "2026-07-27T14:00:00Z",
                }
            ]
        },
        HASH,
    )

    assert records[0].source_record_id == "AL012026"
    assert records[0].payload["display_only_when_active"] is True
    assert adapter.normalize({"activeStorms": []}, HASH) == []
    with pytest.raises(UpstreamSchemaError):
        adapter.normalize({"activeStorms": "invalid"}, HASH)


def test_nws_forecast_preserves_official_period_fields() -> None:
    adapter = NwsForecastAdapter(hourly=True)
    records = adapter.normalize(
        {
            "properties": {
                "generatedAt": "2026-07-27T14:00:00Z",
                "periods": [
                    {
                        "number": 1,
                        "name": "This Hour",
                        "startTime": "2026-07-27T14:00:00Z",
                        "endTime": "2026-07-27T15:00:00Z",
                        "temperature": 88,
                    }
                ],
            }
        },
        HASH,
    )

    assert records[0].payload["forecast_kind"] == "hourly"
    assert records[0].payload["temperature"] == 88
    with pytest.raises(UpstreamSchemaError):
        adapter.normalize({"properties": {}}, HASH)
