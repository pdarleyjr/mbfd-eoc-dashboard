from .adapters.arcgis import ArcGisAdapter, ArcGisSource, DissolvingArcGisAdapter
from .adapters.base import Adapter
from .adapters.coops import CoopsAdapter
from .adapters.eia import EiaRegionDataAdapter
from .adapters.gtfs import MiamiDadeGtfsAdapter
from .adapters.nhc import NhcCurrentStormsAdapter
from .adapters.nws import NwsAlertsAdapter, NwsForecastAdapter, NwsObservationAdapter
from .adapters.pulsepoint import PulsePointAdapter
from .adapters.radar import NoaaRadarStatusAdapter
from .adapters.web import OfficialWebAdapter, OfficialWebSource


def _road_sources() -> list[Adapter]:
    base = (
        "https://services.arcgis.com/3wFbqsFPLeKqOlIK/arcgis/rest/services/"
        "Road_Closures/FeatureServer"
    )
    fhp_fields = (
        "INCIDENTID",
        "TYPEEVENT",
        "DATESTR",
        "COUNTY",
        "LOCATION",
        "REMARKS",
    )
    fl511_fields = (
        "NAME",
        "DESCRIPT",
        "COUNTY",
        "HIGHWAY",
        "DIRECTION",
        "SEVERITY",
        "REPORTED",
        "UPDATED",
    )
    definitions = [
        (
            0,
            "fdem-fhp-closures",
            "FDEM / FHP Road Closures",
            "TYPEEVENT",
            "DATESTR",
            fhp_fields,
        ),
        (
            1,
            "fdem-fhp-crashes",
            "FDEM / FHP Traffic Incidents",
            "TYPEEVENT",
            "DATESTR",
            fhp_fields,
        ),
        (
            4,
            "fdem-fl511-crashes",
            "FDEM / FL511 Traffic Incidents",
            "NAME",
            "UPDATED",
            fl511_fields,
        ),
        (
            5,
            "fdem-fl511-congestion",
            "FDEM / FL511 Congestion",
            "NAME",
            "UPDATED",
            fl511_fields,
        ),
        (
            6,
            "fdem-fl511-construction",
            "FDEM / FL511 Construction",
            "NAME",
            "UPDATED",
            fl511_fields,
        ),
        (
            7,
            "fdem-fl511-other",
            "FDEM / FL511 Other Incidents",
            "NAME",
            "UPDATED",
            fl511_fields,
        ),
    ]
    return [
        ArcGisAdapter(
            ArcGisSource(
                source_id=source_id,
                source_name=source_name,
                url=f"{base}/{layer}",
                category="traffic_incident",
                title_field=title_field,
                observed_field=observed_field,
                poll_interval_seconds=60,
                stale_threshold_seconds=180,
                include_fields=include_fields,
            )
        )
        for (
            layer,
            source_id,
            source_name,
            title_field,
            observed_field,
            include_fields,
        ) in definitions
    ]


def _preliminary_firm_sources() -> list[Adapter]:
    base = "https://gis.miamibeachfl.gov/public/rest/services/mb/PreliminaryFIRM2024/FeatureServer"
    definitions = (
        (
            1,
            "limwa",
            "Limit of Moderate Wave Action",
            "DFIRM_ID",
            "Limit of Moderate Wave Action",
            ("DFIRM_ID", "VERSION_ID", "LIMWA_ID", "SHOWN_FIRM", "SOURCE_CIT"),
        ),
        (
            3,
            "ae",
            "AE — Special Flood Hazard Area with Base Flood Elevation",
            "FLD_ZONE",
            None,
            ("DFIRM_ID", "FLD_AR_ID", "FLD_ZONE", "SFHA_TF", "STATIC_BFE", "V_DATUM"),
        ),
        (
            4,
            "ao",
            "AO — Special Flood Hazard Area with Depth",
            "FLD_ZONE",
            None,
            ("DFIRM_ID", "FLD_AR_ID", "FLD_ZONE", "SFHA_TF", "DEPTH", "LEN_UNIT"),
        ),
        (
            5,
            "ve",
            "VE — Coastal Special Flood Hazard Area",
            "FLD_ZONE",
            None,
            ("DFIRM_ID", "FLD_AR_ID", "FLD_ZONE", "SFHA_TF", "STATIC_BFE", "V_DATUM"),
        ),
        (
            6,
            "x-annual-chance",
            "X — 0.2% to 1% Annual-Chance Flood Hazard",
            "FLD_ZONE",
            None,
            ("DFIRM_ID", "FLD_AR_ID", "FLD_ZONE", "SFHA_TF", "Zone_Subty"),
        ),
        (
            7,
            "x-minimal",
            "X — Area of Minimal Flood Hazard",
            "FLD_ZONE",
            None,
            ("DFIRM_ID", "FLD_AR_ID", "FLD_ZONE", "SFHA_TF", "Zone_Subty"),
        ),
    )
    return [
        (
            DissolvingArcGisAdapter(
                ArcGisSource(
                    source_id=f"miami-beach-preliminary-firm-2024-{slug}",
                    source_name=f"City of Miami Beach Preliminary FIRM 2024 — {name}",
                    url=f"{base}/{layer}",
                    category="flood_zone",
                    title_field=title_field,
                    fixed_title=fixed_title,
                    poll_interval_seconds=86400,
                    stale_threshold_seconds=172800,
                    include_fields=include_fields,
                    geometry_precision=5,
                    max_allowable_offset=0.0001,
                ),
                dissolve_field="FLD_ZONE",
            )
            if layer != 1
            else ArcGisAdapter(
                ArcGisSource(
                    source_id=f"miami-beach-preliminary-firm-2024-{slug}",
                    source_name=f"City of Miami Beach Preliminary FIRM 2024 — {name}",
                    url=f"{base}/{layer}",
                    category="flood_zone",
                    title_field=title_field,
                    fixed_title=fixed_title,
                    poll_interval_seconds=86400,
                    stale_threshold_seconds=172800,
                    include_fields=include_fields,
                    geometry_precision=5,
                    max_allowable_offset=0.0001,
                )
            )
        )
        for layer, slug, name, title_field, fixed_title, include_fields in definitions
    ]


def _arcgis_sources() -> list[Adapter]:
    return [
        ArcGisAdapter(
            ArcGisSource(
                source_id="wpc-day-1-excessive-rainfall",
                source_name="NWS Weather Prediction Center Day 1 Excessive Rainfall Outlook",
                url=(
                    "https://mapservices.weather.noaa.gov/vector/rest/services/"
                    "hazards/wpc_precip_hazards/MapServer/0"
                ),
                category="excessive_rainfall_outlook",
                title_field="outlook",
                id_field="objectid",
                observed_field="issue_time",
                expires_field="end_time",
                poll_interval_seconds=900,
                stale_threshold_seconds=3600,
                include_fields=(
                    "product",
                    "valid_time",
                    "start_time",
                    "dn",
                ),
                geometry_precision=4,
                max_allowable_offset=0.01,
            )
        ),
        ArcGisAdapter(
            ArcGisSource(
                source_id="spc-day-1-convective-outlook",
                source_name="NWS Storm Prediction Center Day 1 Convective Outlook",
                url=(
                    "https://mapservices.weather.noaa.gov/vector/rest/services/"
                    "outlooks/SPC_wx_outlks/MapServer/1"
                ),
                category="severe_weather_outlook",
                title_field="label2",
                id_field="objectid",
                observed_field="issue",
                expires_field="expire",
                poll_interval_seconds=900,
                stale_threshold_seconds=3600,
                include_fields=(
                    "dn",
                    "valid",
                    "label",
                    "stroke",
                    "fill",
                ),
                geometry_precision=4,
                max_allowable_offset=0.01,
            )
        ),
        ArcGisAdapter(
            ArcGisSource(
                source_id="miami-beach-lane-closures",
                source_name="City of Miami Beach Active Lane Closures",
                url=(
                    "https://gis.miamibeachfl.gov/public/rest/services/gc/"
                    "gc_LaneClosures/FeatureServer/0"
                ),
                category="lane_closure",
                title_field="USER_main_address_line_1",
                observed_field="last_edited_date",
                expires_field="USER_expiration_date",
                poll_interval_seconds=120,
                stale_threshold_seconds=360,
                include_fields=(
                    "USER_status_desc",
                    "USER_permit_number",
                    "USER_description",
                    "USER_main_address_line_1",
                    "USER_main_address_line_2",
                    "USER_issue_date",
                    "USER_expiration_date",
                    "last_edited_date",
                ),
            )
        ),
        ArcGisAdapter(
            ArcGisSource(
                source_id="miami-beach-stormwater-pumps",
                source_name="Stormwater Pump Stations — Asset Inventory",
                url=(
                    "https://gis.miamibeachfl.gov/public/rest/services/gc/"
                    "gc_Stormwater/FeatureServer/4"
                ),
                category="stormwater_pump_asset",
                title_field="ASSET_ID",
                observed_field="last_edited_date",
                poll_interval_seconds=21600,
                stale_threshold_seconds=86400,
                include_fields=(
                    "ASSET_ID",
                    "ASSET_TYPE",
                    "ASSET_ADDRESS",
                    "address_ps",
                    "Neighborhood",
                    "OWNED_BY",
                    "MAINT_BY",
                    "last_edited_date",
                ),
            )
        ),
        ArcGisAdapter(
            ArcGisSource(
                source_id="miami-beach-flood-zones",
                source_name="City of Miami Beach Flood Zones",
                url=(
                    "https://gis.miamibeachfl.gov/public/rest/services/gc/"
                    "gc_FloodZonesCounty/MapServer/0"
                ),
                category="flood_zone",
                title_field="FLD_ZONE",
                poll_interval_seconds=86400,
                stale_threshold_seconds=172800,
                geometry_precision=5,
                max_allowable_offset=0.0001,
            )
        ),
        *_preliminary_firm_sources(),
        ArcGisAdapter(
            ArcGisSource(
                source_id="miami-beach-municipal-boundary",
                source_name="Miami-Dade GIS — Miami Beach Municipal Boundary",
                url=(
                    "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/"
                    "Municipal_Boundary_2/FeatureServer/0"
                ),
                category="municipal_boundary",
                title_field="NAME",
                where="NAME='MIAMI BEACH'",
                poll_interval_seconds=86400,
                stale_threshold_seconds=172800,
                geographic_scope=False,
                include_fields=("NAME", "MUNICUID", "MUNICID", "MODIFIEDDATE"),
                geometry_precision=5,
                max_allowable_offset=0.0001,
            )
        ),
        ArcGisAdapter(
            ArcGisSource(
                source_id="miami-dade-hurricane-evacuation-zones",
                source_name="Miami-Dade Hurricane Evacuation Zones",
                url=(
                    "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/"
                    "HurricaneEvacZone_gdb/FeatureServer/0"
                ),
                category="evacuation_zone",
                title_field="ZONEID",
                observed_field="MODIFYDATE",
                poll_interval_seconds=86400,
                stale_threshold_seconds=172800,
                include_fields=("CATEGORY", "ZONEID", "COLOR", "MODIFYDATE"),
                geometry_precision=5,
                max_allowable_offset=0.0001,
            )
        ),
        ArcGisAdapter(
            ArcGisSource(
                source_id="fdem-fl511-traffic-cameras",
                source_name="FDEM / FL511 Traffic Cameras",
                url=(
                    "https://services.arcgis.com/3wFbqsFPLeKqOlIK/arcgis/rest/services/"
                    "FL511_Traffic_Cameras/FeatureServer/0"
                ),
                category="traffic_camera",
                title_field="DESCRIPT",
                id_field="ID",
                poll_interval_seconds=300,
                stale_threshold_seconds=900,
                include_fields=(
                    "DESCRIPT",
                    "COUNTY",
                    "HIGHWAY",
                    "DIRECTION",
                    "IMAGE",
                ),
            )
        ),
        ArcGisAdapter(
            ArcGisSource(
                source_id="miami-dade-hospitals",
                source_name="Miami-Dade GIS Hospital Locations",
                url=(
                    "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/"
                    "Hospital_gdb/FeatureServer/0"
                ),
                category="hospital",
                title_field="NAME",
                where="CITY='MIAMI BEACH' OR ZIPCODE IN ('33139','33140')",
                poll_interval_seconds=86400,
                stale_threshold_seconds=172800,
                include_fields=("NAME", "ADDRESS", "CITY", "ZIPCODE", "PHONE"),
            )
        ),
        ArcGisAdapter(
            ArcGisSource(
                source_id="fdem-florida-hotels",
                source_name="FDEM / Florida DBPR Licensed Hotels",
                url=(
                    "https://services.arcgis.com/3wFbqsFPLeKqOlIK/arcgis/rest/services/"
                    "Florida_Hotels/FeatureServer/0"
                ),
                category="hotel",
                title_field="BUSINESS_NAME",
                id_field="LICENSENO",
                observed_field="LASTINSPDATE",
                where="LL_CITY='MIAMI BEACH' OR LL_ZIP IN ('33139','33140')",
                poll_interval_seconds=86400,
                stale_threshold_seconds=172800,
                include_fields=(
                    "BUSINESS_NAME",
                    "LL_ADDR1",
                    "LL_ADDR2",
                    "LL_CITY",
                    "LL_ZIP",
                    "LIC_TYPE",
                    "LICENSENO",
                    "UNITS",
                    "EZone",
                    "LASTINSPDATE",
                ),
            )
        ),
        ArcGisAdapter(
            ArcGisSource(
                source_id="fema-open-shelters",
                source_name="FEMA National Shelter System — Open Shelters",
                url="https://gis.fema.gov/arcgis/rest/services/NSS/OpenShelters/MapServer/0",
                category="open_shelter",
                title_field="shelter_name",
                id_field="shelter_id",
                where="state='FL'",
                poll_interval_seconds=300,
                stale_threshold_seconds=900,
                geographic_scope=False,
                include_fields=(
                    "shelter_id",
                    "shelter_name",
                    "address",
                    "city",
                    "state",
                    "zip",
                    "shelter_status",
                    "hours_open",
                    "hours_close",
                    "org_name",
                    "ada_compliant",
                    "pet_accommodations_code",
                    "wheelchair_accessible",
                ),
            )
        ),
        ArcGisAdapter(
            ArcGisSource(
                source_id="miami-dade-evacuation-centers",
                source_name="Miami-Dade Evacuation Center Inventory",
                url=(
                    "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/"
                    "EvacuationCenter_gdb/FeatureServer/0"
                ),
                category="evacuation_center",
                title_field="ShlName",
                id_field="DataID",
                observed_field="ModifyDate",
                where="Zipcode IN ('33139','33140') OR City='MIAMI BEACH'",
                poll_interval_seconds=21600,
                stale_threshold_seconds=86400,
                include_fields=(
                    "ShlName",
                    "Address",
                    "City",
                    "Zipcode",
                    "ShlType",
                    "SpeclNeed",
                    "PetFrndly",
                    "ModifyDate",
                ),
            )
        ),
    ]


def _official_web_sources() -> list[Adapter]:
    sources = [
        OfficialWebSource(
            source_id="miami-beach-emergency-notifications",
            source_name="City of Miami Beach Emergency Notifications",
            url=("https://www.miamibeachfl.gov/city-hall/fire/emergency-management/notifications/"),
            selectors=("main article", "main .entry-content", "main"),
            emit_records=False,
        ),
        OfficialWebSource(
            source_id="miami-beach-boil-water",
            source_name="City of Miami Beach Boil-Water Notices",
            url="https://www.miamibeachfl.gov/boil-water-notice/",
            selectors=("main article", "main .entry-content", "main"),
            relevance_terms=("boil water", "miami beach", "33139", "33140"),
            active_section=("Precautionary Boil Water Notices", "Past Notices"),
        ),
        OfficialWebSource(
            source_id="miami-dade-emergency-activation",
            source_name="Miami-Dade Emergency Information",
            url="https://www.miamidade.gov/global/emergency/activation/home.page",
            selectors=("main article", "main .cmp-text", "main"),
            relevance_terms=("activation", "emergency", "miami-dade", "miami beach"),
            active_section=("Emergency Operations Center (EOC)", "Statements & Releases"),
        ),
        OfficialWebSource(
            source_id="miami-dade-transit-updates",
            source_name="Miami-Dade Transit Service Updates",
            url="https://www.miamidade.gov/transportation-publicworks/service_updates.asp",
            selectors=("main article", "main .cmp-text", "main"),
            category="transit",
            relevance_terms=("miami beach", "route", "service", "metrobus", "trolley"),
            emit_records=False,
        ),
        OfficialWebSource(
            source_id="miami-dade-elevator-escalator",
            source_name="Miami-Dade Elevator and Escalator Status",
            url=(
                "https://www.miamidade.gov/global/transportation/tracker/"
                "elevator-escalator-status.page"
            ),
            selectors=("main table", "main .cmp-text", "main"),
            category="transit",
            relevance_terms=("elevator", "escalator", "service", "station"),
            emit_records=False,
        ),
        OfficialWebSource(
            source_id="miami-beach-traffic-advisories",
            source_name="City of Miami Beach Road Closures",
            url="https://www.miamibeachfl.gov/breakasweat/road-closures/",
            selectors=("main article", "main .entry-content", "main"),
            category="traffic_incident",
            emit_records=False,
        ),
        OfficialWebSource(
            source_id="official-causeway-advisories",
            source_name="Miami-Dade Venetian Causeway Project Notices",
            url=(
                "https://www.miamidade.gov/global/transportation/public-works/"
                "venetian-causeway.page"
            ),
            selectors=("main article", "main .cmp-text", "main"),
            category="traffic_incident",
            relevance_terms=("macarthur", "julia tuttle", "venetian", "causeway", "bridge"),
            emit_records=False,
        ),
    ]
    return [OfficialWebAdapter(source) for source in sources]


def source_registry() -> list[Adapter]:
    return [
        PulsePointAdapter(),
        *[EiaRegionDataAdapter(metric) for metric in ("D", "DF", "NG")],
        NwsAlertsAdapter(),
        NwsForecastAdapter(),
        NwsForecastAdapter(hourly=True),
        NwsObservationAdapter(),
        NoaaRadarStatusAdapter(),
        *[
            CoopsAdapter(product)
            for product in (
                "water_level",
                "predicted_water_level",
                "tide_predictions",
                "air_temperature",
                "water_temperature",
                "wind",
                "air_pressure",
            )
        ],
        NhcCurrentStormsAdapter(),
        *_road_sources(),
        *_arcgis_sources(),
        MiamiDadeGtfsAdapter(),
        *_official_web_sources(),
    ]
