# Deployment

Production path: `/opt/mbfd/eoc-dashboard`. Host binding:
`127.0.0.1:8220`. Container-internal listeners are not host-exposed; PostgreSQL
and Redis have no published ports.

```bash
cd /opt/mbfd/eoc-dashboard
git fetch --prune origin
git checkout main
git pull --ff-only origin main
export EOC_RELEASE_SHA="$(git rev-parse HEAD)"
export EOC_BUILD_ID="$(date -u +%Y%m%dT%H%M%SZ)"
docker compose build --pull
docker compose up -d
docker compose ps
curl --fail http://127.0.0.1:8220/health/ready
curl --fail http://127.0.0.1:8220/api/system/version
```

Create `.env` on the server with mode `0600`, fresh database/Redis credentials,
the production origin, `EOC_EIA_API_KEY`, the approved OpenStreetMap tile URL,
and the radar kiosk reset interval. Never copy it into an image, repository,
diagnostic output, or backup manifest. The EIA value is server-side only. EIA
response snapshots are recursively stripped of echoed `api_key` fields before
persistence.

`VITE_MAP_TILE_URL` defaults to the public OpenStreetMap endpoint. If using that
service, preserve its exact HTTPS URL, visible attribution, normal browser
headers/caching, and no prefetch/bulk download. Configure an approved alternate
provider when an availability SLA is required.

`VITE_RADAR_KIOSK_RESET_MINUTES` defaults to 10. In full-screen use, radar
animation stops and returns to the newest service-reported frame after this
interval. NOAA radar imagery is fetched directly by the browser from nowCOAST;
the backend retrieves only WMS metadata and exact available frame times.

Alembic runs before Uvicorn starts. API health remains critical on PostgreSQL and
Redis; Ollama, Maxun, Hermes and PulsePoint are reported independently so a
non-critical public-source failure does not trigger a restart loop.

Rollback:

1. Record current `/api/system/version` and `docker image inspect`.
2. `git checkout <known-good-sha>`.
3. Set release/build identity and rebuild.
4. Run `docker compose up -d`; Alembic migrations must be backward-compatible or
   follow the documented database restore procedure.
5. Verify localhost, Tunnel hostname, Access challenge, and version identity.
