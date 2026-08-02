import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from shapely.geometry import shape

from app.adapters.arcgis import ArcGisAdapter, ArcGisSource, DissolvingArcGisAdapter
from app.adapters.coops import CoopsAdapter
from app.adapters.eia import EiaRegionDataAdapter
from app.adapters.nws import NwsAlertsAdapter
from app.adapters.pulsepoint import PulsePointAdapter
from app.adapters.web import OfficialWebAdapter, OfficialWebSource
from app.errors import UpstreamSchemaError

FIXTURES = Path(__file__).parent / "fixtures"


def load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_pulsepoint_fixture_preserves_advisory_disclaimer_and_units() -> None:
    adapter = PulsePointAdapter()
    records = adapter.normalize(load_json("pulsepoint.json"), "a" * 64)

    assert adapter.retire_missing is True
    assert records[0].payload["disclaimer"] == "PulsePoint advisory feed — not official CAD"
    assert records[0].payload["units"][0]["status"] == "Dispatched"


async def test_eia_fetch_uses_server_key_but_sanitizes_snapshot_body() -> None:
    source_payload = load_json("eia_region_data.json")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_key"] == "server-secret"
        assert request.url.params["frequency"] == "local-hourly"
        assert request.url.params["facets[respondent][]"] == "FPL"
        assert request.url.params["facets[type][]"] == "D"
        assert request.url.params["sort[0][column]"] == "period"
        assert request.url.params["sort[0][direction]"] == "desc"
        return httpx.Response(200, json=source_payload, request=request)

    adapter = EiaRegionDataAdapter("D", api_key="server-secret")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        fetched = await adapter.fetch(client)

    assert b"server-secret" not in fetched.body
    assert "api_key" not in fetched.parsed["request"]["params"]


def test_eia_fixture_normalizes_fpl_scope_without_outage_claims() -> None:
    adapter = EiaRegionDataAdapter("D", api_key="server-secret")
    records = adapter.normalize(load_json("eia_region_data.json"), "e" * 64)

    assert len(records) == 1
    assert records[0].title == "FPL regional grid demand"
    assert records[0].category == "power_grid_status"
    assert records[0].observed_at is not None
    assert records[0].observed_at.isoformat() == "2026-07-28T13:00:00+00:00"
    assert records[0].payload == {
        "respondent": "FPL",
        "respondent_name": "Florida Power & Light Co.",
        "metric_type": "D",
        "metric_name": "Demand",
        "value": 23418,
        "unit": "megawatthours",
        "period": "2026-07-28T09-04:00",
        "frequency": "local-hourly",
        "geographic_scope": "Florida Power & Light balancing authority",
        "scope_note": "Regional grid indicator; not a Miami Beach customer-outage count",
    }
    assert "api_key" not in records[0].source_url


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"response": {"data": []}},
        {
            "response": {
                "frequency": "local-hourly",
                "data": [{"respondent": "MISO", "type": "D", "value": "1"}],
            }
        },
        {
            "response": {
                "frequency": "local-hourly",
                "data": [{"respondent": "FPL", "type": "D", "value": "not-a-number"}],
            }
        },
    ],
)
def test_eia_rejects_empty_mismatched_or_non_numeric_data(payload: object) -> None:
    with pytest.raises(UpstreamSchemaError):
        EiaRegionDataAdapter("D", api_key="server-secret").normalize(payload, "f" * 64)


def test_nws_alert_fixture_preserves_expiration() -> None:
    records = NwsAlertsAdapter().normalize(load_json("nws_alerts.json"), "b" * 64)
    assert records[0].expires_at is not None
    assert records[0].category == "weather_alert"


def test_coops_fixture_labels_observation_not_prediction() -> None:
    records = CoopsAdapter(product="water_level").normalize(load_json("coops.json"), "c" * 64)
    assert records[0].payload["measurement_kind"] == "observed"


def test_arcgis_fixture_normalizes_point_and_fields() -> None:
    source = ArcGisSource(
        source_id="fixture",
        source_name="Fixture",
        url="https://example.gov/FeatureServer/0",
        category="facility",
        title_field="NAME",
        observed_field="UPDATED",
    )
    records = ArcGisAdapter(source).normalize(load_json("arcgis.json"), "d" * 64)
    assert records[0].geography["type"] == "Point"
    assert records[0].payload["STATUS"] == "Source-provided status"


def test_arcgis_query_is_spatially_bounded_and_requests_only_required_fields() -> None:
    source = ArcGisSource(
        source_id="fixture",
        source_name="Fixture",
        url="https://example.gov/FeatureServer/0",
        category="facility",
        title_field="NAME",
        observed_field="UPDATED",
        include_fields=("STATUS", "NAME"),
    )

    query = parse_qs(urlparse(ArcGisAdapter(source).url).query)

    assert query["geometry"] == ["-80.20,25.74,-80.10,25.89"]
    assert query["spatialRel"] == ["esriSpatialRelIntersects"]
    assert query["outFields"] == ["OBJECTID,NAME,UPDATED,STATUS"]
    assert query["geometryPrecision"] == ["6"]


def test_arcgis_query_requests_bounded_display_geometry() -> None:
    source = ArcGisSource(
        source_id="flood",
        source_name="Flood",
        url="https://example.gov/FeatureServer/0",
        category="flood_zone",
        title_field="ZONE",
        geometry_precision=5,
        max_allowable_offset=0.0001,
    )

    query = parse_qs(urlparse(ArcGisAdapter(source).url).query)

    assert query["geometryPrecision"] == ["5"]
    assert query["maxAllowableOffset"] == ["0.0001"]


def test_arcgis_empty_response_is_valid_empty_not_all_clear() -> None:
    source = ArcGisSource(
        source_id="fixture",
        source_name="Fixture",
        url="https://example.gov/FeatureServer/0",
        category="facility",
        title_field="NAME",
    )
    assert ArcGisAdapter(source).normalize({"features": []}, "e" * 64) == []


def test_arcgis_repairs_invalid_polygon_geometry() -> None:
    bowtie = {
        "rings": [
            [
                [-80.15, 25.76],
                [-80.12, 25.79],
                [-80.15, 25.79],
                [-80.12, 25.76],
                [-80.15, 25.76],
            ]
        ]
    }

    geography = ArcGisAdapter._geometry(bowtie)

    assert geography["type"] == "MultiPolygon"
    assert shape(geography).is_valid


def test_arcgis_error_response_is_invalid() -> None:
    source = ArcGisSource(
        source_id="fixture",
        source_name="Fixture",
        url="https://example.gov/FeatureServer/0",
        category="facility",
        title_field="NAME",
    )
    with pytest.raises(UpstreamSchemaError):
        ArcGisAdapter(source).normalize({"error": {"message": "bad query"}}, "f" * 64)


def test_arcgis_dissolves_same_class_polygon_fragments() -> None:
    source = ArcGisSource(
        source_id="flood-fixture",
        source_name="Flood fixture",
        url="https://example.gov/FeatureServer/0",
        category="flood_zone",
        title_field="FLD_ZONE",
        include_fields=("FLD_ZONE",),
    )
    payload = {
        "features": [
            {
                "attributes": {"OBJECTID": 1, "FLD_ZONE": "AE"},
                "geometry": {
                    "rings": [[[-80.14, 25.78], [-80.13, 25.78], [-80.13, 25.79], [-80.14, 25.78]]]
                },
            },
            {
                "attributes": {"OBJECTID": 2, "FLD_ZONE": "AE"},
                "geometry": {
                    "rings": [[[-80.13, 25.78], [-80.12, 25.78], [-80.12, 25.79], [-80.13, 25.78]]]
                },
            },
        ]
    }

    records = DissolvingArcGisAdapter(source, dissolve_field="FLD_ZONE").normalize(
        payload, "0" * 64
    )

    assert len(records) == 1
    assert records[0].source_record_id == "dissolved:AE"
    assert records[0].payload["dissolved_feature_count"] == 2
    assert records[0].geography["type"] in {"Polygon", "MultiPolygon"}


def test_official_web_fixture_is_supplemental_and_cites_url() -> None:
    source = OfficialWebSource(
        source_id="notice-fixture",
        source_name="Official fixture",
        url="https://example.gov/notices",
        selectors=("article",),
    )
    html = (FIXTURES / "official_notice.html").read_text(encoding="utf-8")
    records = OfficialWebAdapter(source).normalize(html, "1" * 64)
    assert records[0].authority_level.value == "supplemental"
    assert records[0].source_url == "https://example.gov/official-advisory"


def test_official_web_missing_selector_reports_layout_change() -> None:
    source = OfficialWebSource(
        source_id="notice-fixture",
        source_name="Official fixture",
        url="https://example.gov/notices",
        selectors=(".not-present",),
    )
    with pytest.raises(UpstreamSchemaError, match="layout"):
        OfficialWebAdapter(source).normalize("<html><body></body></html>", "2" * 64)


def test_official_web_active_section_excludes_archive_content() -> None:
    source = OfficialWebSource(
        source_id="notice-fixture",
        source_name="Official fixture",
        url="https://example.gov/notices",
        selectors=("main",),
        active_section=("Current Notices", "Past Notices"),
        relevance_terms=("miami beach",),
    )
    html = """
    <main>
      <h1>Current Notices</h1>
      <p>Miami Beach water work affects 100 Example Street.</p>
      <h2>Past Notices</h2>
      <p>Miami Beach archived notice must not appear.</p>
    </main>
    """

    records = OfficialWebAdapter(source).normalize(html, "3" * 64)

    assert len(records) == 1
    assert "100 Example Street" in records[0].payload["text"]
    assert "archived notice" not in records[0].payload["text"]


def test_official_web_removes_cms_artifacts_and_builds_a_concise_title() -> None:
    source = OfficialWebSource(
        source_id="notice-fixture",
        source_name="Official fixture",
        url="https://example.gov/notices",
        selectors=("main",),
        relevance_terms=("miami-dade",),
    )
    html = """
    <main>
      ls:end[component-1700000000000]
      ls:begin[component-1700000000001]
      Miami-Dade DEM is monitoring potential Atlantic storms and will provide
      updates if systems threaten the county. Residents should monitor official
      channels for source-backed updates.
      HTML
    </main>
    """

    records = OfficialWebAdapter(source).normalize(html, "5" * 64)

    assert records[0].title == (
        "Miami-Dade DEM is monitoring potential Atlantic storms and will provide "
        "updates if systems threaten the county."
    )
    assert "ls:end" not in records[0].payload["text"]
    assert "ls:begin" not in records[0].payload["text"]
    assert not records[0].payload["text"].endswith("HTML")
    assert len(records[0].title) <= 180


def test_official_web_informational_page_reports_no_current_records() -> None:
    source = OfficialWebSource(
        source_id="notice-fixture",
        source_name="Official fixture",
        url="https://example.gov/notices",
        selectors=("main",),
        emit_records=False,
    )

    assert (
        OfficialWebAdapter(source).normalize(
            "<main>Subscribe to Miami Beach notifications.</main>",
            "4" * 64,
        )
        == []
    )
