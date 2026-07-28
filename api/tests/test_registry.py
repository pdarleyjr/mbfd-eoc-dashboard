from urllib.parse import parse_qs, urlparse

from app.registry import source_registry


def test_registry_has_no_duplicate_source_ids() -> None:
    sources = source_registry()
    ids = [source.source_id for source in sources]
    assert len(sources) == 43
    assert len(ids) == len(set(ids))
    assert {
        "eia-fpl-demand",
        "eia-fpl-day-ahead-demand-forecast",
        "eia-fpl-net-generation",
    } <= set(ids)
    assert "fdem-power-outage-miami-dade" not in ids
    assert "fpl-power-tracker" not in ids


def test_city_preliminary_firm_layers_are_spatially_bounded_and_labeled() -> None:
    sources = [
        source
        for source in source_registry()
        if source.source_id.startswith("miami-beach-preliminary-firm-2024-")
    ]

    assert len(sources) == 6
    assert all(source.category == "flood_zone" for source in sources)
    assert all("Preliminary FIRM 2024" in source.source_name for source in sources)
    assert all("geometry" in parse_qs(urlparse(source.url).query) for source in sources)


def test_evacuation_center_inventory_uses_current_public_feature_service() -> None:
    source = next(
        source
        for source in source_registry()
        if source.source_id == "miami-dade-evacuation-centers"
    )

    assert "EvacuationCenter_gdb/FeatureServer/0/query" in source.url


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
        "power_grid_status",
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
