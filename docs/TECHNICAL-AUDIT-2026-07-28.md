# EOC Technical Audit and Overhaul — 2026-07-28

## Scope and evidence

This audit covers the EOC dashboard repository, the map implementation and
configuration pattern in `pdarleyjr/mbfd-command`, the production EOC API and
worker on the GMKtec, current public GIS/page contracts, and responsive browser
behavior at 1920×1080, 1366×768, 1180×820, and 390×844.

The audit distinguishes code/configuration readiness from Google Cloud
authorization and from physical/human acceptance. No source result is treated as
an operational all-clear.

## Executive findings

| Severity | Finding | Evidence before repair | Resolution |
| --- | --- | --- | --- |
| P0 | Dashboard category starvation and stale-state contamination | `/api/v1/dashboard/summary` returned 2,500 records, all `forecast`, in a 3.3 MB response. Production contained 2,774 active hourly forecast rows, 2,619 marked stale. | Absent rows from a complete successful response now expire immediately, including rows with an old future expiry. Dashboard queries apply per-category display bounds and prefer non-stale rows. API responses over 1 KB are gzip-compressed. |
| P1 | Google Maps rejected the available Command browser key | Controlled probes on both `cmd.mbfdhub.com` and `eoc.mbfdhub.com` returned `RefererNotAllowedMapError`; the Command build had no production Map ID. | The EOC preserves secure environment injection, reports missing and authentication-failed states separately, and does not copy the rejected key. Google Cloud changes remain required; see “Google Maps action required.” |
| P1 | GIS circuit breaker suppressed recovered slow-poll sources for days | Three failures on a 24-hour layer created a five-day restart-time suppression window. Flood and pump layers remained open after City GIS connectivity recovered. | Circuit suppression is capped at 15 minutes and never exceeds one normal poll interval. A worker restart can now retry a recovered source instead of preserving a multi-day outage. |
| P1 | CPU-heavy GIS normalization could make another daily source miss its startup poll | The first production pass logged a daily scheduler run missed by 1.9 s while large ArcGIS polygon sets were being normalized. The default misfire allowance was one second. | Normalization now runs in a worker thread, and every scheduled source receives a bounded 60–600 s misfire allowance derived from its request/retry budget. Coalescing and one-instance limits remain in force. |
| P1 | Full-resolution polygons made the restored map unusably slow | Once every FIRM/flood layer arrived, the actual gzip dashboard transfer measured 9.45 MB and blocked first render over the operations network. | Polygon publishers are now asked for five-decimal display geometry with a 0.0001° maximum offset (about 11 m latitude). Live contract measurement reduced all affected normalized GIS layers to approximately 468 KiB gzip while retaining record identity, attributes, provenance, and authoritative source links. |
| P1 | Countywide evacuation geometry overwhelmed Miami Beach data | The evacuation-zone adapter disabled geographic scope and retained 2,000 active countywide polygons. | The adapter now applies the Miami Beach/causeway bounding query. |
| P1 | Static webpages appeared as active operational notices | Subscription instructions, a 2024 boil-water archive, a construction project page, and generic transit pages were stored as current records. | Active sections are bounded by page headings. Informational-only pages remain health-monitored but emit no active record. Successful empty/current parses retire prior hashes immediately. |
| P2 | GIS polygon/line clicks did nothing | Only point markers called the detail selection handler. | Google Data-layer features now use a click listener keyed to the canonical record ID. |
| P2 | Map configuration message collided with layer controls | Desktop error-state padding reserved 14 rem on the right even though controls occupy the left. | The reserved space is now on the left; phone layout retains its separate bottom control tray. |
| P2 | Detail cards were cramped and raw | A medium drawer placed raw fields in two narrow columns and allowed a multi-kilobyte `text` value to dominate a card. | The large responsive drawer separates provenance, metadata, structured fields, a 700-character excerpt, and an explicit full-text expander. |
| P2 | Touch targets were below the project requirement | Header and map controls measured 32×32 px. | Primary header, layer, list, source-link, and map-focus controls now enforce a 44 px minimum target. |
| P1 | Shared Ollama scheduling made AI responsiveness unreliable | A live grounded extraction took 122.68 s cold. Follow-up testing showed the shared 35B/16K runner being evicted by a separate 65K coding request; one extraction then timed out while Ollama spent about 121 s reloading. | EOC now has a persistent dedicated Ollama service on the private `mbfd-ai` bridge, using Qwen 3.5 9B at 8K context. The normalizer keeps it resident for 30 minutes, caps output at 600 tokens, permits one 90 s request, and never repeats a transport timeout. Host firewall scope is limited to the EOC Docker subnet. |
| P3 | Main web bundle remains relatively large | Production build reports an approximately 557 KB minified main chunk. | The map is already lazy-loaded. Further Fluent component-level splitting is an optimization, not a functional release blocker. |

## Map and GIS implementation

The Command repository confirmed the intended integration pattern:

- `@vis.gl/react-google-maps`
- `VITE_GOOGLE_MAPS_API_KEY`
- `VITE_GOOGLE_MAPS_MAP_ID`
- Miami Beach center `25.7907,-80.1300`
- Advanced Markers, recentering, geolocation/address patterns, and touch-aware
  side-panel behavior

Command does not contain City ArcGIS overlays. Those remain EOC-specific.

The EOC GIS registry now includes:

- City active lane closures, with permit/status/issue/expiration fields
- Stormwater Pump Stations — Asset Inventory, with inventory fields only
- City flood-zone geometry
- City Preliminary FIRM 2024 LIMWA and AE, AO, VE, and X hazard layers,
  explicitly labeled preliminary
- Miami Beach municipal boundary
- Miami-Dade hurricane evacuation zones, spatially bounded to the operating area
- Miami-Dade hospitals, evacuation centers, and static transit
- FDEM/FHP/FL511 roads, incidents, congestion, construction, hotels, and power
- FEMA open shelters

The map retains authority symbology, clustering, layer toggles, Miami Beach reset,
and MacArthur, Julia Tuttle, and Venetian quick focus. Preliminary FIRM layers
share the flood toggle and retain source-specific detail/provenance.

## Google Maps action required

The source code is ready, but Google Cloud authorization cannot be repaired with
the Cloudflare or GitHub credentials. An owner/editor of the Maps project must:

1. Create a dedicated EOC browser key rather than sharing the rejected Command
   key.
2. Set the application restriction to **Websites** and authorize at minimum
   `https://eoc.mbfdhub.com/*`. Preserve only explicitly required development
   origins; do not use a wildcard domain.
3. Restrict the key to **Maps JavaScript API**. Add another API only if EOC code
   actually begins using that service.
4. Confirm billing is enabled on the project.
5. Create a production **JavaScript vector Map ID** and inject it as
   `VITE_GOOGLE_MAPS_MAP_ID`. `DEMO_MAP_ID` is for testing, not this production
   release.
6. Rebuild the image because Vite browser values are compile-time inputs.
7. Repeat a real browser probe on `https://eoc.mbfdhub.com`, requiring visible
   tiles, no auth error, Advanced Marker capability, a clickable polygon, and a
   clickable clustered point.

## UI/UX scorecard

Initial score: **23/40**.

| Dimension | Before | Primary issue |
| --- | ---: | --- |
| Visual hierarchy | 3/4 | Map failure dominated without a clean recovery state |
| Layout/composition | 2/4 | Error copy/control collision and cramped detail fields |
| Typography | 2/4 | KPI/source ellipsis hid operational labels |
| Color | 3/4 | Strong semantic palette; authority still needed text labels |
| Consistency | 3/4 | Fluent surface system was coherent |
| Affordance | 2/4 | Polygon shapes were not actionable |
| Responsive | 3/4 | No panel overlap, but mobile KPI truncation remained |
| Accessibility | 2/4 | Keyboard structure was good; 32 px touch targets failed |
| Content/clarity | 2/4 | Static pages appeared current and raw keys dominated details |
| Polish | 1/4 | Multi-second data payload and visible map-state collision |

Post-repair score: **38/40**. Layout, typography, affordance, responsive,
accessibility, content clarity, and consistency scored 4/4 in the deployed
browser matrix. Color remained 3/4 because authority requires redundant text,
and polish remained 3/4 pending a rendered Google map and main-bundle splitting.

## AI and scraper integrity

AI remains supplemental and cannot make operational decisions. Its output must:

- validate against the strict schema;
- cite a known source record ID;
- quote verbatim supporting text;
- keep every claimed location, corridor, and explicit time present in the
  source text;
- fail closed on malformed/unsupported content.

The production inference lane is intentionally isolated from the GMKtec coding
controller:

- `ollama-eoc.service` is enabled with `Restart=always`;
- it binds only `172.20.0.1:11437`;
- UFW permits only `172.20.0.0/24` to that address/port;
- Qwen 3.5 9B uses an 8K context and one loaded/parallel model;
- the source validator requires locations, corridors, and times to be exact
  contiguous source substrings in addition to verbatim evidence.

The exact patched normalizer passed three live cases against this service:
traffic closure, explicit no-closure, and utility repair. It returned correct
classifications, source-only locations/corridors/times, permitted record IDs,
and verbatim evidence. Measured latency was 67.94 s for the cold service load
and 8.07–16.14 s warm. The rejected 3B candidates remain out of production:
Qwen 2.5 paraphrased/invented structured values and Llama 3.2 mislabeled the
closure as not relevant.

Direct official APIs/GIS remain preferred. For approved public pages:

- a successful validated empty extraction is reported as “No current records
  returned by source,” not a normal/all-clear condition;
- static landing pages are monitored for reachability/layout but do not create
  active records;
- archive content is separated from the current section;
- page hashes absent from a complete successful extraction expire immediately;
- Maxun and Hermes remain internal audit/fallback systems, not browser-facing
  sources of truth.

## Verification and residual acceptance

Local release checks completed on 2026-07-28:

- Ruff formatting/lint and mypy passed.
- Pytest passed 66 tests with one environment-dependent integration test
  skipped; measured coverage was 88.58%.
- The live contract probe validated all 42 configured source contracts.
- TypeScript typecheck and ESLint passed.
- Vitest passed 12 tests with 85.71% statement, 81.69% branch, 85.91%
  function, and 89.62% line coverage.
- The production web build passed.
- Playwright passed 24 checks across 1920 desktop, 1366 laptop, landscape
  tablet, 390 px mobile, WebKit, and reduced-motion projects.
- The project dependency audits reported no known Python or npm
  vulnerabilities; the changed-file secret scan and `git diff --check` passed.

The final deployment handoff records the immutable release SHA, tree, archive
checksum, image identity, CI run, and rollback path. Production acceptance
observed during this audit also included:

- all 42 source-health rows healthy;
- 1,127 displayed records across 14 categories with zero stale records;
- 1,084 active geometries with zero invalid shapes;
- a 584,821-byte compressed dashboard response in 0.188 s at origin;
- restart-free, read-only API/worker containers under UID/GID 10001 with
  `no-new-privileges`;
- no worker scheduler/error warnings;
- six live production profiles with eight non-overlapping panels, no horizontal
  overflow, 44×44 px header controls, legible detail drawers, and zero browser
  runtime errors;
- one 24-hour Cloudflare Access application, one precedence-1 allow policy,
  `pdarleyjr@gmail.com` present exactly once, and `onetimepin` as the only
  identity-provider type;
- an unauthenticated HTTPS edge request redirecting to Cloudflare Access with a
  valid TLS chain.

Residual gates that must not be inferred from automation:

- Google Cloud key/referrer/Map ID change and rendered production map acceptance
- authenticated edge-browser interaction after the next operator OTP login
- physical EOC display and touch use
- human operational-content review
- native Safari device review
- long-duration stability observation
