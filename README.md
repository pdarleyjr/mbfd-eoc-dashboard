# Miami Beach Emergency Management Dashboard

Private, read-only common operating picture for Miami Beach, ZIP codes 33139/33140,
and the MacArthur, Julia Tuttle, and Venetian access corridors.

The application is independent of MBFD Hub, MBFD Command, and TF Field App. It
consumes public or already-normalized sources only and does not implement write
workflows, CAD, AVL, SCADA, PHI, patient data, resource requests, or private
operational systems.

## Architecture

- React 19, strict TypeScript, Fluent UI, TanStack Query, Zustand, Zod, Google Maps.
- FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 16/PostGIS, Redis.
- APScheduler worker with Redis locks, bounded retries, circuit breakers, sanitized
  immutable snapshots, and visible last-known-good behavior.
- Single-origin container exposed on the host only at `127.0.0.1:8220`.
- Cloudflare Tunnel and Access provide authenticated HTTPS ingress.

## Local validation

```powershell
cd D:\GitHub_Repos\EOC\mbfd-eoc-dashboard
npm ci
npm run typecheck
npm run lint
npm run test:coverage
npm run test:e2e

cd api
py -3 -m pip install ".[dev]"
py -3 -m ruff format --check app tests scripts alembic
py -3 -m ruff check app tests scripts alembic
py -3 -m mypy app
py -3 -m pytest
```

Copy `.env.example` to `.env` only on an authorized development or production
host. Generate fresh PostgreSQL and Redis passwords. Browser map values are
compiled into the SPA and therefore must be HTTP-referrer restricted; they are
not server secrets.

## Honest-display contract

- PulsePoint is always labeled **advisory** and never CAD.
- Empty results are not translated into “normal,” “open,” “all clear,” or “no
  shelters exist.”
- Retrieval time is distinct from source observation time.
- Static pump, hospital, and hotel inventories never imply live status.
- A failed poll retains last-known-good records and marks them stale.
- AI-assisted extraction is supplemental, schema-validated, evidence-cited, and
  cannot overwrite authoritative records.

See [Architecture](docs/ARCHITECTURE.md), [Data Sources](docs/DATA-SOURCES.md),
[Deployment](docs/DEPLOYMENT.md), and
[Acceptance Tests](docs/ACCEPTANCE-TESTS.md).
