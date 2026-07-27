import json
from pathlib import Path

import pytest

from app.adapters.arcgis import ArcGisAdapter, ArcGisSource
from app.adapters.coops import CoopsAdapter
from app.adapters.nws import NwsAlertsAdapter
from app.adapters.pulsepoint import PulsePointAdapter
from app.adapters.web import OfficialWebAdapter, OfficialWebSource
from app.errors import UpstreamSchemaError

FIXTURES = Path(__file__).parent / "fixtures"


def load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_pulsepoint_fixture_preserves_advisory_disclaimer_and_units() -> None:
    records = PulsePointAdapter().normalize(load_json("pulsepoint.json"), "a" * 64)
    assert records[0].payload["disclaimer"] == "PulsePoint advisory feed — not official CAD"
    assert records[0].payload["units"][0]["status"] == "Dispatched"


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


def test_arcgis_empty_response_is_valid_empty_not_all_clear() -> None:
    source = ArcGisSource(
        source_id="fixture",
        source_name="Fixture",
        url="https://example.gov/FeatureServer/0",
        category="facility",
        title_field="NAME",
    )
    assert ArcGisAdapter(source).normalize({"features": []}, "e" * 64) == []


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
    assert records[0].source_url == source.url


def test_official_web_missing_selector_reports_layout_change() -> None:
    source = OfficialWebSource(
        source_id="notice-fixture",
        source_name="Official fixture",
        url="https://example.gov/notices",
        selectors=(".not-present",),
    )
    with pytest.raises(UpstreamSchemaError, match="layout"):
        OfficialWebAdapter(source).normalize("<html><body></body></html>", "2" * 64)
