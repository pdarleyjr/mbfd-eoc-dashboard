# Maxun

Maxun is an internal browser-extraction fallback, not a system of record. Direct
official APIs and deterministic parsers remain preferred.

Required production controls:

- Upstream official Maxun `v0.0.44` deployment pinned to verified multi-platform
  image digests and release commit `ca3138a2dbc81564d16d1cf1beca2b52bef96104`.
- No host or Tunnel publication of the administrative UI, backend, browser,
  database, or Redis.
- Strong generated internal credentials stored outside Git.
- Attachment to the internal EOC/AI networks only.
- Ollama URL `http://host.docker.internal:11434`.
- Bounded CPU/memory and `no-new-privileges` where the upstream image supports it.

EOC robots use the prefix `MBFD-EOC-` and cover only approved official pages.
Results enter the ingestion service, schema validation, source health, and
last-known-good store; the browser never queries Maxun.

Health includes backend, browser worker, latest robot success, schema validity,
empty-output detection, and layout-change detection. `eoc-scrape-audit` performs
the previous/current comparison and deduplicated escalation.

The hardened deployment definition is `maxun/compose.yaml`. It publishes no host
ports. Its browser image requires the upstream `SYS_ADMIN` and unconfined seccomp
settings; those exceptions apply only to the isolated browser container. Backend
readiness uses Maxun's root response because upstream v0.0.44 does not implement
a `/health` route.
