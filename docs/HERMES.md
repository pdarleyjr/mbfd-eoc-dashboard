# Hermes Extensions

Three review-only skills are supplied under `hermes/skills`:

- `eoc-source-check`: queries source health, thresholds repeated failures,
  deduplicates alerts, classifies sanitized failure context, and sends one
  recovery notification.
- `eoc-scrape-audit`: compares direct/Maxun output with the prior successful
  result and reports empty content, missing selectors, schema/count drift.
- `eoc-public-brief`: produces a concise internal context summary with source
  record IDs and explicit stale/unavailable categories.

Install into the existing Hermes user skill directory without replacing existing
skills. Use the existing Telegram configuration; no bot token is copied into this
repository. Hermes may notify after threshold but must not change selectors,
restart production, publish public instructions, or approve operational decisions.

The skills query the Access-independent localhost API from the GMKtec. State and
sanitized reports live below `/var/lib/mbfd-eoc/hermes` with restrictive
permissions.
