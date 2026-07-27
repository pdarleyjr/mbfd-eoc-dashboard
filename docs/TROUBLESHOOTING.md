# Troubleshooting

## Dashboard loads but data is degraded

Inspect `/api/v1/sources/health`; do not restart merely because a publisher is
empty or unavailable. Verify source URL/schema with `scripts/probe_sources.py`.
Repeated failures open the circuit and preserve visibly stale LKG records.

## Scraper layout changed

Confirm official URL, look for an API/XHR replacement, capture a sanitized
fixture, update deterministic selectors and tests, then release. Do not let
Hermes/Qwen edit production.

## Map configuration unavailable

Verify both build-time browser values, HTTP referrer restrictions, Maps
JavaScript API enablement, CSP console messages, and Map ID. Rebuild is required
after changing `VITE_*`.

## Readiness is 503

PostgreSQL and Redis are critical. Check container health, credentials, network,
and Alembic revision. Ollama/Maxun/Hermes/PulsePoint are reported but do not make
the process restart-loop.

## Tunnel/Access

Verify localhost first, then cloudflared health/ingress ordering, proxied DNS,
Access app/policy, and unauthenticated challenge. Preserve existing tunnel routes.

## Release mismatch

Compare `git rev-parse HEAD`, OCI revision label, running image ID and
`/api/system/version`; a branch name or remote-tracking ref is not deployment proof.
