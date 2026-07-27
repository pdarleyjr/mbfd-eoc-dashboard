---
name: eoc-scrape-audit
description: Compare MBFD EOC direct and Maxun scraper output with the prior successful result.
---

# EOC Scrape Audit

Query the localhost source-health API and approved internal Maxun health/robot
interfaces. Compare sanitized current output with the prior successful manifest
under `/var/lib/mbfd-eoc/hermes/scrape-audit`.

Flag missing selectors, empty page/content, invalid schema, unexpected count
changes, missing required provenance fields, or a layout-change state. Do not
interpret a legitimate zero-result machine-readable feed as a scraper failure.

Save a timestamped sanitized report. Alert the existing private Telegram target
only when the condition persists for the configured threshold or is a confirmed
schema/layout break. Send one recovery notice. Never edit selectors, robots,
source configuration, or restart production automatically.
