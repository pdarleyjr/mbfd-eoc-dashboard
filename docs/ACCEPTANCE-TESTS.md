# Acceptance Tests

Automated gates:

- Backend Ruff format/lint, strict MyPy, 80% minimum branch-aware coverage,
  fixture/source-schema tests, PostGIS migration/integration test.
- Frontend Prettier, strict TypeScript, ESLint, 80% minimum line/statement/
  function/branch coverage, production build, zero high/critical npm audit.
- Playwright at 1920×1080, 1920×900, 1858×970, 1366×768, 1180×820,
  390×844, WebKit, and reduced motion: load, stale/LKG display, rich
  PulsePoint/road/notice/grid cards, drawers, layer toggles, keyboard skip link,
  selected-map synchronization, keyboard lines/polygons, no primary-page scroll
  at 1920×1080, and reachable bottom panels at short/narrow viewports.
- A real-tile keyless-map probe requires HTTP 200 OpenStreetMap tiles, visible
  attribution/street labels, cleared loading state, and working controls. Normal
  CI intercepts tile requests to avoid load against the public service.
- Container image build and secret scan in CI.

Production gates:

1. All four Compose containers healthy; restart persistence verified.
2. Version SHA equals GitHub `main` and image label.
3. Localhost origin succeeds and is not bound to a non-loopback host address.
4. Tunnel hostname uses HTTPS and unauthenticated traffic encounters Access.
5. Authenticated desktop/tablet browser: logo, Fluent layout, visible keyless
   map (or authorized Google enhancement), marker/layer/focus controls,
   clickable/keyboard point-line-polygon records, drawers, and
   fresh/stale/unavailable semantics.
6. Source health proves live PulsePoint, weather, coastal, NHC, roads, power,
   shelters, facilities, transit and public-page polling; empty valid collections
   remain honest.
7. Ollama model check, grounded schema test, Maxun internal health/robot audit,
   and Hermes skill dry runs pass.
8. No public PostgreSQL, Redis, Ollama, Maxun or Hermes listeners.
9. Fresh backup and isolated restore smoke succeed.
10. All three EIA FPL sources have fresh `D`, `DF`, and `NG` records; values are
    labeled regional and no obsolete FDEM/static FPL outage source is active.

Human/physical observations, Access OTP completion, and long-duration publisher
behavior must be reported separately; automation must not fabricate them.
