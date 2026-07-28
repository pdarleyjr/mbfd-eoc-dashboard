# Final Implementation Report

## 2026-07-28 operational-map and EIA completion

This section supersedes older implementation evidence retained below for audit
history. It contains no credential values. The final release SHA and CI run for
the commit containing this report are recorded in the release handoff because a
Git commit cannot embed its own not-yet-created identity.

### Implementation and verified candidate

- Operational-map/EIA implementation commit:
  `e5e2ab36f9909763f1e60248593573e5301db246`
- Source tree:
  `eccfc6b63594fe64f8d6997531e58d36081d0a1b`
- Green CI:
  `https://github.com/pdarleyjr/mbfd-eoc-dashboard/actions/runs/30377588635`
- Immutable archive SHA-256:
  `5cd6583eb75b1e2913a3823d5104f239d62b1b499df9c7b56208bdb8818ba8c5`
- Production build:
  `prod-20260728T162955Z-e5e2ab36`
- Production image:
  `sha256:ca99ec558d8b658e61acbbf0ac8a6748175cf378aaf65eed96c736271e2f1192`
- Rollback retained at:
  `/opt/mbfd/releases/eoc/rollback-742d960c-eia-20260728T165007Z`

CI passed backend, PostGIS integration, frontend, Chromium/WebKit Playwright,
container/Maxun, npm and Python dependency audits, and gitleaks. The local
release gate passed 78 backend tests with one explicit PostGIS integration skip,
88.42% branch-aware coverage, Ruff, strict mypy, TypeScript, ESLint, Vitest,
production build, and targeted Playwright regression coverage.

### Delivered corrections

- Leaflet/OpenStreetMap provides a visible keyless operational map while Google
  remains optional. It renders clustered points, authoritative lines/polygons,
  layer toggles, causeway focus, selection synchronization, keyboard actions,
  and visible OpenStreetMap attribution.
- PulsePoint cards render call type/code, active/recent and live/stale state,
  address, call time, units, unit status, overflow count, coordinate status, and
  the non-CAD disclaimer. Card selection focuses and highlights the mapped
  incident; the detail drawer renders structured advisory units.
- Road cards render location, status, concise source text, permit, applicable
  start/end times, freshness, authority, and a details action.
- Official-notice extraction removes observed `ls:begin`, `ls:end`, and trailing
  `HTML` artifacts, produces deterministic concise titles, and preserves clean
  source text for details.
- Short desktop and responsive layouts make the bottom panels reachable rather
  than clipping them. Exact regression profiles include 1920×1080, 1858×970,
  1920×900, 1366×768, 1180×820, 390×844, reduced motion, and WebKit.
- A production browser probe found that Fluent `size="small"` left the map
  quick-focus buttons only 24 px tall on a fine-pointer desktop. A red
  Playwright regression reproduced it; all four causeway/reset controls now
  enforce 44×44 minimum targets.

### EIA integration and truth boundary

The obsolete `fdem-power-outage-miami-dade` and static `fpl-power-tracker`
definitions are removed. The server-only EIA credential is stored in the
mode-0600 production environment and is never embedded in Vite assets, snapshots,
logs, this report, or repository content.

Live pre-deployment contract checks and fresh production worker polls succeeded
for:

- `eia-fpl-demand` (`D`);
- `eia-fpl-day-ahead-demand-forecast` (`DF`);
- `eia-fpl-net-generation` (`NG`).

The observed responses contained numeric `megawatthours` values, periods,
respondent `FPL`, and the geographic scope `Florida Power & Light balancing
authority`. Recursively sanitized snapshot bodies contained zero `api_key`
fields. The UI and canonical payload state that these are regional grid
indicators, not Miami Beach customer-outage counts.

The first production poll exposed two historical health rows left by the removed
adapters: the registry contained 43 sources while PostgreSQL returned 45 health
rows. The containing release now reconciles the database against the configured
registry at worker startup. Records from removed sources are expired and marked
stale, their health rows are deleted, raw snapshots remain available for
provenance, and an empty registry is rejected to prevent accidental mass
retirement.

### Backup, deployment, and acceptance boundaries

A fresh checksum-verified backup is retained at
`/opt/mbfd/backups/eoc-dashboard/20260728T162556Z`. Its isolated restore
returned 8,117 records, 4,468 geometry rows, zero invalid geometries, PostGIS
3.5.7, and 8,516 snapshot files totaling 184,450,322 bytes. The temporary
database and volume were removed after verification.

The release uses a stage/swap deployment with an automatic rollback trap. An
initial activation correctly rolled back because HTTP readiness preceded
Docker's `healthy` state by several seconds. The corrected gate waits for both
application readiness and container health before accepting the swap; no
partial release was left active.

Automation does not establish physical EOC display/touch acceptance, native
Safari behavior, human operational-content approval, Google-rendered-map
acceptance, or long-duration stability. Playwright WebKit is not reported as
native Safari.

---

Evidence was collected on 2026-07-27 EDT. This report contains no credential
values, Access identities, bot tokens, database passwords, map keys, tunnel
tokens, session cookies, or authorization headers.

## Release identity

- Private repository: `https://github.com/pdarleyjr/mbfd-eoc-dashboard`
- Canonical branch: `main`
- Verified application candidate: `57e35f6fcdb23549d3bca9115a0439ebe08f5994`
- Candidate source tree: `91af6960541da5b7a914c276dccaae18d74ef1f7`
- Candidate archive SHA-256:
  `1dcdcca246f116958035da24c825aa615c226752726d376dc97b9c1a7e2686fa`
- Green candidate CI:
  `https://github.com/pdarleyjr/mbfd-eoc-dashboard/actions/runs/30296062946`
- CI conclusions: backend, frontend, integration, container/Maxun validation,
  and dependency/security all `success`. Frontend CI included Chromium and
  WebKit Playwright projects. Dependency/security included npm audit,
  pip-audit, and gitleaks.
- Candidate production image digest:
  `sha256:1e1cf3f2b5ca7937dc3304cb627147bfd9cf7c23684fb442bf390b079afd66dd`
- Candidate build ID: `prod-20260727T190144Z-57e35f6f`
- Production source: `/opt/mbfd/eoc-dashboard`
- Production URL: `https://eoc.mbfdhub.com`
- Rollback source:
  `/opt/mbfd/releases/eoc/rollback-56b2f499-retry-20260727T190435Z`

The canonical final release is the commit containing this report. A Git commit
cannot embed its own cryptographic SHA or its not-yet-created CI run URL. The
release handoff therefore supplies those two immutable values after this report
is committed, CI passes, and production is redeployed. Final acceptance requires
`/api/system/version.release_sha` and the image revision label to equal that
containing commit.

## Production runtime and security

The candidate deployment returned:

```json
{
  "application": "mbfd-eoc-dashboard",
  "release_sha": "57e35f6fcdb23549d3bca9115a0439ebe08f5994",
  "build_id": "prod-20260727T190144Z-57e35f6f",
  "environment": "production"
}
```

Readiness was `ready`: PostgreSQL, Redis, PulsePoint, Ollama, and Maxun were
`healthy`. Hermes is reported as `not_configured` because no authenticated
Hermes health URL is exposed to the dashboard; its systemd and cron evidence is
recorded separately below. `/metrics` returned HTTP 200.

The API and worker ran as `10001:10001`, with a read-only root filesystem and
`no-new-privileges:true`. PostgreSQL and Redis had no Compose port bindings.
The API had only `127.0.0.1:8220:8220`. Host listeners observed on 5432 and 6379
were separate loopback-only Docker proxies; neither was an EOC Compose
publication. All six Maxun services had empty host port bindings.

After a full dashboard-stack restart, API, worker, PostgreSQL, and Redis all
returned `running/healthy` on the same candidate image. PostgreSQL remained at
3,029 records, raw snapshot files increased from 789 to 793, and a short-lived
Redis acceptance sentinel survived the restart and was then removed.

## Cloudflare

The fresh control-plane snapshot showed tunnel configuration version 18 with 25
ingress rules. Exactly one rule maps `eoc.mbfdhub.com` to
`http://127.0.0.1:8220`; the existing terminal `http_status:404` catch-all
remains last. Warp routing remains disabled.

Exactly one proxied CNAME maps the EOC hostname to the existing GMKtec tunnel.
Exactly one 24-hour self-hosted Access application protects the hostname. It has
one precedence-1 allow policy using the copied `email_domain`, `email`, and
`email` include types; identity values are intentionally omitted.

A fresh unauthenticated HTTPS request verified TLS and returned HTTP 302 to the
Cloudflare Access login flow. The origin binds only to loopback. Authenticated
final-host browser acceptance still requires an authorized Access OTP/session.

## Data ingestion and persistence

At 2026-07-27 15:45 EDT:

- 36 sources: 32 healthy, one `invalid_response`, and three `unavailable`.
- The three unavailable City of Miami Beach GIS sources were lane closures,
  flood zones, and stormwater pumps. Each timed out and had an open circuit.
- Miami-Dade evacuation centers returned one ArcGIS error response with its
  circuit still closed.
- PostgreSQL held 3,200 canonical records from 23 record-producing sources.
- All 3,200 records had source URL and raw snapshot provenance.
- 423 records were explicitly stale-retained. Representative stale reasons were
  `Record absent from a successful current source response`.
- 2,708 records had geometry and zero geometries were invalid.
- PostGIS was 3.5.7.
- The raw-snapshot catalog and filesystem both persisted; the later snapshot
  contained 925 records totaling 25,597,366 bytes.
- The dashboard response was intentionally capped at 2,500 records and labeled
  aggregate source health `stale`; it did not fabricate a healthy operational
  state.

The upstream source counts are a point-in-time observation and can change on
later scheduler runs. No claim is made that unavailable public publishers were
repaired by this deployment.

## Backup and isolated restore

Fresh backup:
`/opt/mbfd/backups/eoc-dashboard/20260727T191807Z`.

Both `eoc.dump` and `raw-snapshots.tar.gz` passed `SHA256SUMS`. The isolated
restore returned 3,024 records, 2,688 geometry rows, zero invalid geometries, and
PostGIS 3.5.7. The snapshot archive restored 754 files totaling 23,831,417
bytes. The live database remained at 3,024 records before and after the smoke
test. Cleanup left zero temporary restore databases and zero temporary restore
volumes.

## Ollama/Qwen

The 2026-07-28 audit superseded the shared 35B configuration documented by the
original rollout. Production now uses a dedicated `ollama-eoc.service` on the
private `mbfd-ai` bridge with `qwen3.5:9b`, an 8K context, a 600-token output
bound, and a 90-second single-request ceiling. The strict Pydantic schema,
known-record-ID requirement, verbatim evidence check, and source-substring
checks remain mandatory. See `TECHNICAL-AUDIT-2026-07-28.md` for the live
contention diagnosis and acceptance timings.

## Maxun

Maxun uses official upstream `v0.0.44` images pinned by digest. The browser image
has no `v0.0.44` tag upstream and is pinned to its observed `latest` digest.
Backend, frontend, browser, PostgreSQL, Redis, and MinIO were all healthy and
had no host port bindings. Only the isolated browser retained its required
browser sandbox exception; the other services did not inherit it.

Three clearly named robots have successful stored runs:

- `MBFD-EOC-Emergency-Notifications`: 40,666 markdown characters.
- `MBFD-EOC-Boil-Water-Notices`: 59,334 markdown characters.
- `MBFD-EOC-Road-Closures`: 54,279 markdown characters.

An earlier boil-water run was aborted after an upstream namespace-cleanup race;
the subsequent run succeeded. Dashboard readiness now reports Maxun `healthy`,
but Maxun remains non-critical while direct official adapters continue working.

## Hermes

The three EOC skills are installed at the Hermes service skill path, owned by
`mbfd-aiops:mbfd-aiops`, mode 0600. The existing Telegram configuration was not
changed.

Exactly three EOC jobs are active:

- `eoc-source-check`, every five minutes, local delivery.
- `eoc-scrape-audit`, every 30 minutes, local delivery.
- `eoc-public-brief`, daily at 07:00 EDT, existing Telegram delivery.

The EOC jobs use the dedicated mode-0700 service work directory
`/var/lib/mbfd-eoc/hermes/workdir`. A first invocation exposed an inherited
working-directory permission error; a manual retry then exceeded five minutes
and its exact tick process was terminated without stopping the gateway. After
the work-directory correction, the gateway's scheduled source check completed
with `Last run: ok` at 15:37 EDT and wrote a mode-0600 threshold/deduplication
state file. The gateway remained active.

The public brief was not manually triggered because doing so would publish to an
external Telegram target. Its first scheduled delivery and the scrape-audit
result remain observation gates; their active schedules are not reported as
successful delivery evidence.

## Browser acceptance

The actual production runtime was tested through an SSH loopback tunnel, not a
mock server:

| Profile | Layout/overflow | Interaction and runtime result |
| --- | --- | --- |
| Chromium 1920x1080 | Three columns; no vertical or horizontal page overflow | Passed |
| Chromium 1366x768 | Two columns; vertical page flow; no horizontal overflow | Passed |
| Chromium tablet 1180x820 | Two columns; 44px touch controls; no horizontal overflow | Passed |
| Chromium phone 390x844 | One column; 44px touch controls; no horizontal overflow | Passed |
| Chromium reduced motion | Three columns; media preference matched | Passed |
| Playwright WebKit engine 1366x768 | Two columns; no horizontal overflow | Passed |

Across the matrix, the MBFD logo loaded; the source-health and record-detail
drawers opened; official links were HTTPS; Flood zones toggled; keyboard focus
reached the skip link; CSP was present; and a service worker registered.
Chromium/WebKit runs emitted no console, page, failed-request, or HTTP-error
responses. The mobile source drawer used the visible `Review every source`
control. The 1920 desktop fit without page scrolling; narrower layouts
intentionally used vertical document flow.

The Google Maps component correctly displayed its configuration-unavailable
state. Causeway focus controls, rendered map tiles, clusters, and live markers
were not accepted because no authorized HTTP-referrer-restricted browser key and
Map ID were available.

## Open gates

- Supply an authorized Google Maps browser key restricted to
  `https://eoc.mbfdhub.com/*` plus an approved Map ID; then rebuild and verify
  the rendered map, markers, clustering, geometry layers, and causeway controls.
- Complete an authorized Cloudflare Access OTP login and repeat the production
  browser matrix through `https://eoc.mbfdhub.com`, including final-host API,
  static asset, CSP, and service-worker checks.
- Observe a successful scheduled Hermes scrape audit and the first authorized
  daily brief delivery. Do not test the latter by sending an unapproved message.
- Recheck the three timed-out City GIS endpoints and the current Miami-Dade
  evacuation-centers ArcGIS response; publisher recovery is external to this
  release.
- Safari, physical TV/tablet hardware, human EOC operator, and long-duration
  acceptance were not observed and are not claimed.

The deployment is production-capable behind Access with the explicit blockers
above. It is not reported as fully accepted for the operational map or the
unobserved human/physical/long-duration gates.
