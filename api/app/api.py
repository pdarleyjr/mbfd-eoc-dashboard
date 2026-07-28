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
    VersionResponse,
)

router = APIRouter()
Session = Annotated[AsyncSession, Depends(session_dependency)]

CATEGORY_GROUPS: dict[str, list[str]] = {
    "incidents": ["pulsepoint_call"],
    "weather": ["weather_alert", "forecast"],
    "coastal": ["coastal_observation"],
    "tropical": ["tropical"],
    "traffic": ["traffic_incident", "lane_closure"],
    "utilities": ["power_outage_summary", "stormwater_pump_asset"],
    "shelters": ["open_shelter", "evacuation_center"],
    "facilities": ["hospital", "hotel"],
    "transit": ["transit"],
    "notices": ["official_notice"],
    "map": [
        "pulsepoint_call",
        "traffic_incident",
        "lane_closure",
        "weather_alert",
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
    "forecast": 40,
    "coastal_observation": 100,
    "tropical": 50,
    "traffic_incident": 200,
    "lane_closure": 200,
    "power_outage_summary": 10,
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
    power = next((record for record in records if record.category == "power_outage_summary"), None)
    healthy_sources = sum(item.state is SourceHealthState.HEALTHY for item in health)

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

    kpis = [
        kpi(
            "pulsepoint",
            "PulsePoint Active Calls",
            len(active_calls),
            "PulsePoint advisory",
            "pulsepoint_call",
            max((item.retrieved_at for item in active_calls), default=None),
        ),
        kpi(
            "alerts",
            "Active NWS Alerts",
            len(alerts),
            "National Weather Service",
            "weather_alert",
            max((item.retrieved_at for item in alerts), default=None),
        ),
        kpi(
            "roads",
            "Road & Access Incidents",
            len(road),
            "Official public traffic sources",
            "traffic_incident",
            max((item.retrieved_at for item in road), default=None),
        ),
        kpi(
            "shelters",
            "Open Shelter Records",
            len(shelters),
            "FEMA Open Shelters",
            "open_shelter",
            max((item.retrieved_at for item in shelters), default=None),
        ),
        kpi(
            "power",
            "Miami-Dade Power Outage Percentage",
            power.payload.get("Pct_Out") if power else None,
            "FDEM public summary",
            "power_outage_summary",
            power.retrieved_at if power else None,
        ),
        kpi(
            "sources",
            "Healthy Data Sources",
            healthy_sources,
            "Dashboard source monitoring",
            "source_health",
            datetime.now(UTC),
        ),
    ]
    return DashboardSummary(
        metadata=_metadata(records, health),
        kpis=kpis,
        records=records,
        source_health=health,
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
