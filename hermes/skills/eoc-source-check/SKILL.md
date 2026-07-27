---
name: eoc-source-check
description: Audit MBFD EOC source health and send thresholded internal recovery/failure notifications.
---

# EOC Source Check

1. GET `http://127.0.0.1:8220/api/v1/sources/health`.
2. Validate the response; never include credentials, raw exceptions, headers, or
   unbounded source content in an alert.
3. Treat `invalid_response`, `scraper_layout_changed`, `unavailable`, and
   consecutive failures as degraded. Empty valid records are not failures.
4. Persist deduplication state in `/var/lib/mbfd-eoc/hermes/source-check.json`.
5. Notify the existing private Hermes Telegram target only after three
   consecutive checks or the configured threshold. Include source ID, safe state,
   failure count, last success, LKG and circuit state.
6. Send exactly one recovery notice after the source returns healthy.
7. Qwen may classify the safe failure summary as network, publisher, schema,
   layout, or unknown. It may not change configuration or restart services.

Do not publish public instructions or infer operational status from source health.
