# EOC Technical Audit and Overhaul — 2026-07-28

## Scope and evidence

This audit covers the EOC dashboard repository, the map implementation and
configuration pattern in `pdarleyjr/mbfd-command`, the production EOC API and
worker on the GMKtec, current public GIS/page contracts, and responsive browser
behavior at 1920×1080, 1920×900, 1858×970, 1366×768, 1180×820, and
390×844.

The audit distinguishes code/configuration readiness from Google Cloud
authorization and from physical/human acceptance. No source result is treated as
an operational all-clear.

## Executive findings

| Severity | Finding | Evidence before repair | Resolution |
| --- | --- | --- | --- |
| P0 | The dashboard had no visible operational map when Google credentials were absent or rejected | The production screenshot showed a configuration message in place of all map context, even though the dashboard must remain useful without a paid map key. | Leaflet/OpenStreetMap is now the automatic keyless/auth-failure fallback with visible attribution, loading/error state, clustering, all configured GIS layers, keyboard-actionable shapes, focus controls, selected-feature highlighting, and resize/full-screen reflow. Google remains optional. |
| P1 | Power data mixed obsolete/outage-oriented sources with the wrong operational meaning | The registry included the FDEM outage layer and a static FPL tracker even though the requested source is EIA regional grid operating data. | Both sources were removed. Three server-side authenticated EIA-930 adapters now request FPL `D`, `DF`, and `NG`, sanitize echoed API keys before snapshots, and label every value as balancing-authority regional data rather than municipal/customer outage data. |
| P1 | PulsePoint, roads, and notices did not expose enough operational context | Cards omitted unit state and call state, flattened road fields, and displayed CMS scrape artifacts such as `ls:begin`, `ls:end`, and trailing `HTML`. | PulsePoint cards now distinguish active/recent and live/stale, show code/address/unit status with overflow and missing-data states, and focus the selected map marker. Road cards expose address, status, permit, summary, dates, authority, freshness, and detail access. Notice cleanup is deterministic and tested against the observed artifacts. |
| P1 | Short desktop displays clipped the bottom dashboard row | At 1858×970 the page shell hid the facilities, utility, and source-health panels; richer cards increased the risk at 1920×900. | Wide/short layouts reserve header and stale-banner rows explicitly and make the dashboard content the scroll container. Automated tests scroll the final panel into view and verify full record text at both exact viewports. |
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

The EOC map/source registry now includes:

- City active lane closures, with permit/status/issue/expiration fields
- Stormwater Pump Stations — Asset Inventory, with inventory fields only
- City flood-zone geometry
- City Preliminary FIRM 2024 LIMWA and AE, AO, VE, and X hazard layers,
  explicitly labeled preliminary
- Miami Beach municipal boundary
- Miami-Dade hurricane evacuation zones, spatially bounded to the operating area
- Miami-Dade hospitals, evacuation centers, and static transit
- FDEM/FHP/FL511 roads, incidents, congestion, construction, and hotels
- EIA-930 FPL regional demand, day-ahead demand forecast, and net generation
- FEMA open shelters

The map retains authority symbology, clustering, layer toggles, Miami Beach reset,
and MacArthur, Julia Tuttle, and Venetian quick focus. Preliminary FIRM layers
share the flood toggle and retain source-specific detail/provenance.

Leaflet/OpenStreetMap is the default whenever Google key/Map ID configuration is
absent or Google reports authentication failure. The public tile endpoint is a
configurable non-secret image-build input. Its use keeps visible attribution,
normal browser headers/caching, and no prefetching or bulk download. Google Maps
remains an optional enhanced renderer and is no longer a prerequisite for an
operational map.

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
- Pytest passed 78 tests with one environment-dependent integration test
  deselected; measured branch-aware coverage was 88.42%.
- The registry contains 43 unique sources. Fixture/schema tests cover all three
  EIA adapters, including recursive API-key removal. Sanitized live contract
  checks and fresh production worker polls passed for FPL demand, day-ahead
  demand forecast, and net generation.
- Production reconciliation retires records and deletes health rows for sources
  removed from the configured registry while preserving raw snapshots. This
  prevents the retired FDEM outage and static FPL tracker sources from inflating
  current source-health counts after an upgrade.
- TypeScript typecheck and ESLint passed.
- Vitest passed 14 tests with 88.88% statement, 89.91% branch, 87.36%
  function, and 91.12% line coverage.
- The production web build passed.
- Playwright passed 56 checks across 1920×1080, 1920×900, 1858×970,
  1366×768, 1180×820, 390×844, WebKit, and reduced-motion projects. A
  separate real-network probe returned successful OpenStreetMap tile responses
  and captured visible labels/attribution.
- The project dependency audits reported no known Python or npm
  vulnerabilities; the changed-file secret scan and `git diff --check` passed.

The final deployment handoff records the immutable release SHA, tree, archive
checksum, image identity, CI run, and rollback path. Baseline production
acceptance observed before this completion pass included:

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
