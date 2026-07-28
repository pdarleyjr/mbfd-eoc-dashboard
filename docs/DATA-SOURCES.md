# Data Sources

All source data is public. EIA requires a server-side API key; the other listed
sources are unauthenticated. The live contract probe is
`python scripts/probe_sources.py`. Empty valid collections remain empty and do
not become an all-clear state.

| Source | Authority | Poll / stale | Scope and mapping |
| --- | --- | --- | --- |
| Existing normalized PulsePoint X1012 proxy | Advisory | 15 s active, 45 s idle / 90 s | Miami Beach records supplied by the established proxy; call/address/unit fields preserved; never CAD |
| NWS alerts API | Authoritative | 45 s / 120 s | Miami Beach point; alert feature geometry and official timestamps |
| NWS point, forecast, hourly forecast | Authoritative | 5 min / 15 min | Point 25.7907,-80.1300; official period fields |
| NOAA CO-OPS station 8723214 | Authoritative | 330 s observations, 6 h predictions / 15 min or 12 h | Water level, tide predictions, wind, air/water temperature, pressure; observed/predicted explicit |
| NHC `CurrentStorms.json` | Authoritative | 5 min / 15 min | Current products only; empty list produces no tropical product |
| FDEM Road Closures layers 0,1,4,5,6,7 | Authoritative | 60 s / 3 min | FHP/FL511 closures, crashes, congestion, construction, other; local geometry/corridor filter |
| EIA-930 FPL demand (`D`) | Authoritative regional grid data | 15 min / 2 h | Latest local-hourly Florida Power & Light balancing-authority demand; not a municipal or customer-outage feed |
| EIA-930 FPL day-ahead demand forecast (`DF`) | Authoritative regional grid data | 15 min / 2 h | Latest local-hourly FPL balancing-authority forecast; not a municipal or customer-outage feed |
| EIA-930 FPL net generation (`NG`) | Authoritative regional grid data | 15 min / 2 h | Latest local-hourly FPL balancing-authority generation; not a municipal or customer-outage feed |
| FDEM Florida Hotels layer 0 | Authoritative inventory | 24 h / 48 h | Miami Beach/33139/33140 licensed locations and rooms; never occupancy |
| Miami Beach Lane Closures layer 0 | Authoritative | 2 min / 10 min | Active published lane-closure records |
| Miami Beach Stormwater layer 4 | Authoritative inventory | 6 h / 24 h | Named “Stormwater Pump Stations — Asset Inventory”; no operating state |
| Miami Beach Flood Zones layer 0 | Authoritative inventory | 24 h / 48 h | Published polygon geometry |
| Miami Beach Preliminary FIRM 2024 layers 1, 3–7 | Authoritative preliminary inventory | 24 h / 48 h | LIMWA plus AE, AO, VE, and X hazard geometries; explicitly labeled preliminary and spatially bounded to the Miami Beach operating area |
| Miami-Dade Municipal Boundary layer 0 | Authoritative inventory | 24 h / 48 h | Miami Beach boundary geometry |
| Miami-Dade Hurricane Evacuation Zones layer 0 | Authoritative inventory | 24 h / 48 h | Published zones; not an evacuation order |
| Miami-Dade Hospitals layer 0 | Authoritative inventory | 24 h / 48 h | Name/location/category only; capacity/diversion fields excluded |
| Miami-Dade EvacuationCenter_gdb layer 0 | Authoritative inventory | 6 h / 24 h | Current public FeatureServer replacing retired 311CRM layer 78; static inventory and distinct from open shelters |
| FEMA OpenShelters layer 0 | Authoritative | 5 min / 15 min | Florida source-status records; zero records does not mean no shelters exist |
| Miami-Dade static GTFS | Authoritative schedule | 6 h / 12 h | Miami Beach-relevant routes, stops and shapes; no Swiftly real-time data |

Publisher roots:

- `https://api.weather.gov`
- `https://api.tidesandcurrents.noaa.gov`
- `https://www.nhc.noaa.gov`
- `https://api.eia.gov/v2/electricity/rto/region-data/data/`
- `https://www.eia.gov/electricity/gridmonitor/`
- `https://services.arcgis.com/3wFbqsFPLeKqOlIK`
- `https://gis.miamibeachfl.gov/public/rest/services`
- `https://services.arcgis.com/8Pc9XBTAsYuxx9Ny`
- `https://giswspro.miamidade.gov/arcgis/rest/services`
- `https://gis.fema.gov/arcgis/rest/services/NSS/OpenShelters`
- `https://www.miamidade.gov/transit/googletransit/current/google_transit.zip`

ArcGIS adapters request `outSR=4326`, validate feature/attribute structure, retain
only configured fields for sensitive inventories, and document scope through the
source-health registry. Representative sanitized fixtures live in
`api/tests/fixtures`.

The fragmented Preliminary FIRM polygon layers are dissolved by official
`FLD_ZONE` class after complete retrieval. This preserves full class geometry
while avoiding thousands of overlapping browser features; the payload records
the number of source fragments represented.

EIA requests require `EOC_EIA_API_KEY`, which is server-side only and is never
compiled into the SPA. The adapter requests one newest `local-hourly` row for
respondent `FPL` and metric `D`, `DF`, or `NG`, validates respondent/type,
period, numeric value, and unit, and stores the EIA Grid Monitor as the official
source link. EIA responses echo request parameters, so every recursively nested
`api_key` field is removed before the sanitized response is serialized or saved
as a raw snapshot. The previous FDEM outage layer and static FPL tracker are not
registered; the dashboard explicitly labels EIA values as regional grid
indicators rather than local outage counts.

To add an adapter: implement `Adapter.fetch` and `normalize`, declare authority,
poll/stale intervals, timeout, retry/circuit policy, empty semantics and scope;
add sanitized valid/empty/malformed fixtures; register it; run unit, live contract,
and PostGIS integration checks.
