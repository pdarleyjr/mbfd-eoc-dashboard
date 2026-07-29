# Architecture

## Runtime

```text
Cloudflare Access -> Cloudflare Tunnel -> 127.0.0.1:8220
                                      -> FastAPI + compiled React SPA
                                      -> APScheduler worker
                                      -> PostgreSQL 16 / PostGIS
                                      -> Redis

Internal-only: Ollama/Qwen, Hermes, Maxun
Public read-only sources: PulsePoint normalized proxy, official APIs/GIS/feeds/pages
```

FastAPI is the only browser origin. PostgreSQL and Redis are attached only to the
internal Compose network. API and worker also join the existing `mbfd-ai` network
to reach approved internal services.

## Ingestion contract

Each adapter fetches, validates, hashes and stores a raw public snapshot,
normalizes into the strict provenance envelope, applies a source-specific
geographic filter, deduplicates by `(source_id, source_record_id)`, persists to
PostgreSQL, and publishes cache invalidation through Redis.

Redis locks prevent concurrent runs. Polls have bounded timeouts, two retries,
5–10% jitter, a circuit breaker after three consecutive failures, and
last-known-good retention. Initial jobs are staggered to avoid bursts against a
single public publisher.

`canonical_records.geography` preserves GeoJSON for clients; `geom` stores SRID
4326 PostGIS geometry with a GiST index. The local prefilter covers the municipal
island and buffered access corridors. The official municipal boundary is ingested
as an authoritative map layer.

## Data semantics

The precedence order is official API/GIS/feed, then PulsePoint advisory, then
official-page extraction. Lower-authority sources supplement; they do not replace
higher-authority values. Source observation, publication, retrieval, and
expiration timestamps remain distinct.

## Frontend

The dense Fluent light layout follows the supplied Microsoft-style visual
reference: header, six defensible KPI tiles, large operational map, right-side
operational panels, and lower source/facility panels. Drawers hold detail so the
primary 1920×1080 view does not vertically scroll. Keyboard, touch, reduced
motion, and responsive laptop/tablet layouts are tested.

The service worker caches only the application shell and last successful
same-origin dashboard responses. It does not cache PHI or private operational data.

The operational map uses one Leaflet renderer for points, lines, polygons,
official hazard outlooks, active NHC products, and NOAA MRMS radar. The backend
polls radar capabilities metadata; the browser requests only the selected WMS
frame and, during playback, the next frame. Radar is static at the latest frame
until an operator selects Play.
