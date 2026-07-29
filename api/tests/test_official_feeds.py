import io
import zipfile

import pytest

from app.adapters.coops import CoopsAdapter
from app.adapters.gtfs import MiamiDadeGtfsAdapter
from app.adapters.nhc import NhcCurrentStormsAdapter
from app.adapters.nws import NwsForecastAdapter, NwsObservationAdapter
from app.adapters.radar import NoaaRadarStatusAdapter
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
                    "latitudeNumeric": 25.2,
                    "longitudeNumeric": -75.1,
                    "lastUpdate": "2026-07-27T14:00:00Z",
                    "forecastTrack": {
                        "issuance": "2026-07-27T14:00:00Z",
                        "kmzFile": "https://www.nhc.noaa.gov/alex-track.kmz",
                    },
                }
            ],
            "gis_documents": {
                "https://www.nhc.noaa.gov/alex-track.kmz": """
                    <kml xmlns="http://www.opengis.net/kml/2.2">
                      <Document><Placemark><LineString><coordinates>
                        -75.1,25.2,0 -76.0,26.0,0 -77.0,27.0,0
                      </coordinates></LineString></Placemark></Document>
                    </kml>
                """,
            },
        },
        HASH,
    )

    assert {record.payload["product_kind"] for record in records} == {"center", "forecast_track"}
    center = next(record for record in records if record.payload["product_kind"] == "center")
    track = next(record for record in records if record.payload["product_kind"] == "forecast_track")
    assert center.source_record_id == "AL012026:center"
    assert center.geography == {"type": "Point", "coordinates": [-75.1, 25.2]}
    assert center.payload["display_only_when_active"] is True
    assert track.geography["type"] == "LineString"
    assert track.source_url == "https://www.nhc.noaa.gov/alex-track.kmz"
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


def test_nws_observation_preserves_station_and_measured_fields() -> None:
    records = NwsObservationAdapter().normalize(
        {
            "station": {
                "id": "KMIA",
                "name": "Miami International Airport",
                "geometry": {"type": "Point", "coordinates": [-80.29, 25.79]},
            },
            "observation": {
                "timestamp": "2026-07-29T12:53:00Z",
                "temperature": {"value": 30.0, "unitCode": "wmoUnit:degC"},
                "relativeHumidity": {"value": 72.0, "unitCode": "wmoUnit:percent"},
                "windSpeed": {"value": 20.0, "unitCode": "wmoUnit:km_h-1"},
                "windGust": {"value": 30.0, "unitCode": "wmoUnit:km_h-1"},
                "visibility": {"value": 16093.4, "unitCode": "wmoUnit:m"},
                "barometricPressure": {"value": 101320, "unitCode": "wmoUnit:Pa"},
                "precipitationLastHour": {"value": 2.54, "unitCode": "wmoUnit:mm"},
            },
        },
        HASH,
    )

    assert len(records) == 1
    assert records[0].category == "weather_observation"
    assert records[0].payload["station_id"] == "KMIA"
    assert records[0].payload["temperature"]["value"] == 30.0
    assert records[0].geography["type"] == "Point"


def test_coops_distinguishes_current_prediction_and_high_low_tides() -> None:
    predicted = CoopsAdapter("predicted_water_level").normalize(
        {"predictions": [{"t": "2026-07-29 13:00", "v": "0.581"}]},
        HASH,
    )
    tides = CoopsAdapter("tide_predictions").normalize(
        {
            "predictions": [
                {"t": "2026-07-29 13:33", "v": "0.595", "type": "H"},
                {"t": "2026-07-29 19:46", "v": "-0.011", "type": "L"},
            ]
        },
        HASH,
    )

    assert predicted[0].payload["product"] == "predicted_water_level"
    assert predicted[0].payload["measurement_kind"] == "predicted"
    assert {record.payload["tide_type"] for record in tides} == {"H", "L"}
    assert all(record.payload["product"] == "tide_predictions" for record in tides)


def test_radar_capabilities_emit_exact_service_reported_frames() -> None:
    xml = (
        __import__("pathlib").Path(__file__).parent / "fixtures" / "radar_capabilities.xml"
    ).read_text(encoding="utf-8")

    record = NoaaRadarStatusAdapter().normalize(xml, HASH)[0]

    assert record.category == "radar_status"
    assert record.observed_at.isoformat() == "2026-07-29T12:48:14+00:00"
    assert record.payload["frame_times"] == [
        "2026-07-29T12:36:01.000Z",
        "2026-07-29T12:40:03.000Z",
        "2026-07-29T12:44:17.000Z",
        "2026-07-29T12:48:14.000Z",
    ]
    assert record.payload["latest_frame_time"] == "2026-07-29T12:48:14.000Z"
    assert record.payload["update_frequency_seconds"] == 240
    assert record.payload["layer_name"] == "conus_base_reflectivity_mosaic"
    assert record.payload["service_url"].startswith("https://nowcoast.noaa.gov/")
    assert record.payload["legend_url"].startswith("https://nowcoast.noaa.gov/")


@pytest.mark.parametrize(
    "xml",
    [
        "<not-wms />",
        """
        <WMS_Capabilities xmlns="http://www.opengis.net/wms">
          <Capability><Layer><Layer>
            <Name>conus_base_reflectivity_mosaic</Name>
          </Layer></Layer></Capability>
        </WMS_Capabilities>
        """,
    ],
)
def test_radar_capabilities_reject_missing_layer_contract(xml: str) -> None:
    with pytest.raises(UpstreamSchemaError):
        NoaaRadarStatusAdapter().normalize(xml, HASH)
