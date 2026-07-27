from urllib.parse import parse_qs, urlparse

from app.registry import source_registry


def test_registry_has_no_duplicate_source_ids() -> None:
    sources = source_registry()
    ids = [source.source_id for source in sources]
    assert len(sources) == 36
    assert len(ids) == len(set(ids))


def test_registry_covers_required_operational_categories() -> None:
    categories = {source.category for source in source_registry()}
    assert {
        "pulsepoint_call",
        "weather_alert",
        "forecast",
        "coastal_observation",
        "tropical",
        "traffic_incident",
        "lane_closure",
        "power_outage_summary",
        "open_shelter",
        "hospital",
        "hotel",
        "transit",
        "official_notice",
        "stormwater_pump_asset",
    } <= categories


def test_scraped_sources_are_marked_supplemental() -> None:
    scraped = [
        source for source in source_registry() if source.source_type == "official_web_scrape"
    ]
    assert scraped
    assert all(source.authority_level == "supplemental" for source in scraped)
    assert all(source.url.startswith("https://") for source in scraped)
    assert all("traffic-advisories" not in source.url for source in scraped)
    assert all("communications/emergency-notifications" not in source.url for source in scraped)


def test_road_sources_request_only_layer_specific_fields() -> None:
    sources = {
        source.source_id: set(parse_qs(urlparse(source.url).query)["outFields"][0].split(","))
        for source in source_registry()
        if source.source_id.startswith("fdem-fhp-") or source.source_id.startswith("fdem-fl511-")
    }
    assert sources["fdem-fhp-closures"] == {
        "OBJECTID",
        "INCIDENTID",
        "TYPEEVENT",
        "DATESTR",
        "COUNTY",
        "LOCATION",
        "REMARKS",
    }
    assert sources["fdem-fhp-crashes"] == sources["fdem-fhp-closures"]
    expected_fl511 = {
        "OBJECTID",
        "NAME",
        "DESCRIPT",
        "COUNTY",
        "HIGHWAY",
        "DIRECTION",
        "SEVERITY",
        "REPORTED",
        "UPDATED",
    }
    assert all(
        fields == expected_fl511 for source_id, fields in sources.items() if "fl511" in source_id
    )
