from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import session_dependency
from .repository import Repository
from .schemas import (
    CanonicalRecord,
    DashboardKpi,
    DashboardSummary,
    RecordsResponse,
    ResponseMetadata,
    SourceHealth,
    SourceHealthState,
    SourceHealthSummary,
    VersionResponse,
)

router = APIRouter()
Session = Annotated[AsyncSession, Depends(session_dependency)]

CATEGORY_GROUPS: dict[str, list[str]] = {
    "incidents": ["pulsepoint_call"],
    "weather": [
        "weather_alert",
        "weather_observation",
        "forecast",
        "excessive_rainfall_outlook",
        "severe_weather_outlook",
    ],
    "coastal": ["coastal_observation"],
    "radar": ["radar_status"],
    "tropical": ["tropical"],
    "traffic": ["traffic_incident", "lane_closure"],
    "utilities": ["power_grid_status", "stormwater_pump_asset"],
    "shelters": ["open_shelter", "evacuation_center"],
    "facilities": ["hospital", "hotel"],
    "transit": ["transit"],
    "notices": ["official_notice"],
    "map": [
        "pulsepoint_call",
        "traffic_incident",
        "lane_closure",
        "weather_alert",
        "excessive_rainfall_outlook",
        "severe_weather_outlook",
        "flood_zone",
        "evacuation_zone",
        "open_shelter",
        "evacuation_center",
        "hospital",
        "hotel",
        "stormwater_pump_asset",
        "transit",
        "tropical",
        "municipal_boundary",
    ],
}

# Keep every operational category represented even when a high-volume feed has
# future-dated rows. Limits are category-specific display bounds, not source
# record counts or claims about upstream completeness.
DASHBOARD_CATEGORY_LIMITS: dict[str, int] = {
    "pulsepoint_call": 100,
    "weather_alert": 50,
    "weather_observation": 10,
    "forecast": 40,
    "radar_status": 5,
    "excessive_rainfall_outlook": 50,
    "severe_weather_outlook": 50,
    "coastal_observation": 100,
    "tropical": 50,
    "traffic_incident": 200,
    "lane_closure": 200,
    "power_grid_status": 10,
    "stormwater_pump_asset": 200,
    "open_shelter": 100,
    "evacuation_center": 100,
    "hospital": 150,
    "hotel": 300,
    "transit": 500,
    "official_notice": 100,
    "flood_zone": 500,
    "evacuation_zone": 250,
    "municipal_boundary": 20,
}


async def _dashboard_records(repository: Repository) -> list[CanonicalRecord]:
    records: list[CanonicalRecord] = []
    for category, limit in DASHBOARD_CATEGORY_LIMITS.items():
        records.extend(await repository.list_records([category], limit=limit))
    return records


def _metadata(records: list[CanonicalRecord], health: list[SourceHealth]) -> ResponseMetadata:
    now = datetime.now(UTC)
    observed: list[datetime] = []
    for record in records:
        observation = record.observed_at or record.published_at
        if observation is not None:
            observed.append(observation)
    last_successes = [item.last_success for item in health if item.last_success]
    states = {item.state for item in health}
    source_state = (
        SourceHealthState.UNAVAILABLE
        if states and states == {SourceHealthState.UNAVAILABLE}
        else SourceHealthState.STALE
        if any(record.stale for record in records)
        else SourceHealthState.DELAYED
        if any(
            state
            in {
                SourceHealthState.DELAYED,
                SourceHealthState.INVALID_RESPONSE,
                SourceHealthState.SCRAPER_LAYOUT_CHANGED,
                SourceHealthState.UNAVAILABLE,
            }
            for state in states
        )
        else SourceHealthState.HEALTHY
    )
    latest_observation = max(observed, default=None)
    return ResponseMetadata(
        generated_at=now,
        source_observation_time=latest_observation,
        data_age_seconds=(
            max(0, int((now - latest_observation).total_seconds())) if latest_observation else None
        ),
        stale=any(record.stale for record in records),
        source_authority=sorted(
            {record.authority_level for record in records},
            key=lambda level: level.value,
        ),
        source_health=source_state,
        last_successful_refresh=max(last_successes, default=None),
        empty_state=None if records else "No current records returned by source",
    )


def _source_health_summary(health: list[SourceHealth]) -> SourceHealthSummary:
    critical_groups: tuple[tuple[str, str, tuple[str, ...]], ...] = (
        ("PulsePoint", "prefix", ("pulsepoint",)),
        ("NWS Alerts", "exact", ("nws-alerts",)),
        ("NOAA Radar", "exact", ("noaa-mrms-radar-status",)),
        ("NHC", "exact", ("nhc-current-storms",)),
        (
            "Roads",
            "prefix",
            (
                "miami-beach-lane-closures",
                "fdem-fhp-",
                "fdem-fl511-",
                "fl511-",
            ),
        ),
        ("CO-OPS", "prefix", ("coops-",)),
    )

    def matches(item: SourceHealth, mode: str, identifiers: tuple[str, ...]) -> bool:
        if mode == "exact":
            return item.source_id in identifiers
        return any(item.source_id.startswith(identifier) for identifier in identifiers)

    unavailable: list[str] = []
    critical_healthy = 0
    for label, mode, identifiers in critical_groups:
        members = [item for item in health if matches(item, mode, identifiers)]
        if any(item.state is SourceHealthState.HEALTHY for item in members):
            critical_healthy += 1
        else:
            unavailable.append(label)

    return SourceHealthSummary(
        critical_healthy=critical_healthy,
        critical_total=len(critical_groups),
        all_healthy=sum(item.state is SourceHealthState.HEALTHY for item in health),
        all_total=len(health),
        unavailable_critical=unavailable,
    )


async def _records_response(session: AsyncSession, group: str) -> RecordsResponse:
    repository = Repository(session)
    records = await repository.list_records(CATEGORY_GROUPS[group])
    health = await repository.list_health()
    relevant_ids = {record.source_id for record in records}
    relevant_health = [item for item in health if item.source_id in relevant_ids] or health
    return RecordsResponse(
        metadata=_metadata(records, relevant_health),
        records=records,
    )


@router.get("/api/v1/incidents", response_model=RecordsResponse)
async def incidents(session: Session) -> RecordsResponse:
    return await _records_response(session, "incidents")


@router.get("/api/v1/weather", response_model=RecordsResponse)
async def weather(session: Session) -> RecordsResponse:
    return await _records_response(session, "weather")


@router.get("/api/v1/coastal", response_model=RecordsResponse)
async def coastal(session: Session) -> RecordsResponse:
    return await _records_response(session, "coastal")


@router.get("/api/v1/radar/status", response_model=RecordsResponse)
async def radar_status(session: Session) -> RecordsResponse:
    return await _records_response(session, "radar")


@router.get("/api/v1/tropical", response_model=RecordsResponse)
async def tropical(session: Session) -> RecordsResponse:
    return await _records_response(session, "tropical")


@router.get("/api/v1/traffic", response_model=RecordsResponse)
async def traffic(session: Session) -> RecordsResponse:
    return await _records_response(session, "traffic")


@router.get("/api/v1/utilities", response_model=RecordsResponse)
async def utilities(session: Session) -> RecordsResponse:
    return await _records_response(session, "utilities")


@router.get("/api/v1/shelters", response_model=RecordsResponse)
async def shelters(session: Session) -> RecordsResponse:
    return await _records_response(session, "shelters")


@router.get("/api/v1/facilities", response_model=RecordsResponse)
async def facilities(session: Session) -> RecordsResponse:
    return await _records_response(session, "facilities")


@router.get("/api/v1/transit", response_model=RecordsResponse)
async def transit(session: Session) -> RecordsResponse:
    return await _records_response(session, "transit")


@router.get("/api/v1/notices", response_model=RecordsResponse)
async def notices(session: Session) -> RecordsResponse:
    return await _records_response(session, "notices")


@router.get("/api/v1/map/features", response_model=RecordsResponse)
async def map_features(session: Session) -> RecordsResponse:
    return await _records_response(session, "map")


@router.get("/api/v1/sources/health", response_model=list[SourceHealth])
async def source_health(session: Session) -> list[SourceHealth]:
    return await Repository(session).list_health()


@router.get("/api/v1/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(session: Session) -> DashboardSummary:
    repository = Repository(session)
    records = await _dashboard_records(repository)
    health = await repository.list_health()
    active_calls = [
        record
        for record in records
        if record.category == "pulsepoint_call" and record.payload.get("state") == "active"
    ]
    alerts = [record for record in records if record.category == "weather_alert"]
    road = [record for record in records if record.category in {"traffic_incident", "lane_closure"}]
    shelters = [record for record in records if record.category == "open_shelter"]
    power = next(
        (
            record
            for record in records
            if record.category == "power_grid_status" and record.payload.get("metric_type") == "D"
        ),
        None,
    )
    health_summary = _source_health_summary(health)

    def count_kpi_updated_at(
        kpi_records: list[CanonicalRecord],
        source_ids: set[str],
    ) -> datetime | None:
        record_updates = [item.retrieved_at for item in kpi_records]
        source_updates = [
            item.last_success
            for item in health
            if item.source_id in source_ids and item.last_success is not None
        ]
        return max((*record_updates, *source_updates), default=None)

    def kpi(
        identifier: str,
        label: str,
        value: int | float | str | None,
        source: str,
        category: str,
        updated_at: datetime | None,
    ) -> DashboardKpi:
        return DashboardKpi(
            id=identifier,
            label=label,
            value=value,
            unavailable=value is None,
            source=source,
            updated_at=updated_at,
            detail_category=category,
        )

    def grid_value(record: CanonicalRecord | None) -> str | None:
        if record is None:
            return None
        value = record.payload.get("value")
        if not isinstance(value, int | float) or isinstance(value, bool):
            return None
        unit = record.payload.get("unit")
        suffix = "MWh" if unit == "megawatthours" else str(unit or "").strip()
        rendered = f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"
        return f"{rendered} {suffix}".strip()

    kpis = [
        kpi(
            "pulsepoint",
            "Active Calls",
            len(active_calls),
            "PulsePoint advisory",
            "pulsepoint_call",
            count_kpi_updated_at(active_calls, {"pulsepoint-x1012"}),
        ),
        kpi(
            "alerts",
            "Active NWS Alerts",
            len(alerts),
            "National Weather Service",
            "weather_alert",
            count_kpi_updated_at(alerts, {"nws-alerts"}),
        ),
        kpi(
            "roads",
            "Road & Access Incidents",
            len(road),
            "Official public traffic sources",
            "traffic_incident",
            count_kpi_updated_at(
                road,
                {
                    "fdem-fhp-crashes",
                    "fdem-fl511-crashes",
                    "fdem-fl511-congestion",
                    "fdem-fl511-construction",
                    "fdem-fl511-other",
                    "miami-beach-lane-closures",
                    "miami-beach-traffic-advisories",
                    "official-causeway-advisories",
                },
            ),
        ),
        kpi(
            "shelters",
            "Open Shelter Records",
            len(shelters),
            "FEMA Open Shelters",
            "open_shelter",
            count_kpi_updated_at(shelters, {"fema-open-shelters"}),
        ),
        kpi(
            "power",
            "FPL Regional Grid Demand",
            grid_value(power),
            "EIA-930 · FPL regional; not local outage data",
            "power_grid_status",
            (power.observed_at or power.retrieved_at) if power else None,
        ),
        kpi(
            "sources",
            "Critical Feeds",
            f"{health_summary.critical_healthy}/{health_summary.critical_total}",
            (
                f"{health_summary.all_healthy}/{health_summary.all_total} "
                "all configured sources healthy"
            ),
            "source_health",
            datetime.now(UTC),
        ),
    ]
    return DashboardSummary(
        metadata=_metadata(records, health),
        kpis=kpis,
        records=records,
        source_health=health,
        health_summary=health_summary,
    )


@router.get("/api/system/version", response_model=VersionResponse)
async def version() -> VersionResponse:
    settings = get_settings()
    return VersionResponse(
        release_sha=settings.release_sha,
        build_id=settings.build_id,
        environment=settings.environment,
        generated_at=datetime.now(UTC),
    )
