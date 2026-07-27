# Maxun

Maxun is an internal browser-extraction fallback, not a system of record. Direct
official APIs and deterministic parsers remain preferred.

Required production controls:

- Upstream official Maxun deployment pinned to a recorded commit.
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
