# Official Public-Page Extraction

The acquisition order is machine-readable official data, public page XHR, direct
deterministic HTML parsing, internal Maxun browser extraction, and finally
evidence-grounded Qwen structuring.

Configured supplemental targets:

- FPL Power Tracker.
- City of Miami Beach emergency notifications.
- City boil-water notices.
- Miami-Dade emergency activation and County services/closures.
- Miami-Dade Transit service updates.
- Miami-Dade elevator/escalator status.
- City traffic advisories.
- Miami-Dade Venetian Causeway project notices.

Every result is `official_web_scrape` / `supplemental`, carries its source URL and
retrieval time, and is filtered for Miami Beach, 33139, 33140, or an access
corridor. A missing selector becomes `scraper_layout_changed`; an empty page is
not a normal condition. Duplicate text is hashed and collapsed.

Static subscription, project-information, or status landing pages are monitored
for reachability and layout but do not emit an active operational record.
Current/archive pages use bounded heading sections. A successful validated empty
or changed extraction retires records absent from that response immediately;
last-known-good records are retained only when the refresh itself fails.

Repair procedure:

1. Confirm the official URL and look for a supported JSON/RSS/XHR replacement.
2. Save a sanitized current HTML fixture.
3. Update deterministic selectors and fixture tests.
4. Run `eoc-scrape-audit`; compare count and schema with the prior successful run.
5. Deploy through the normal release process. Hermes and Qwen may diagnose but
   must not alter selectors or production configuration autonomously.

CAPTCHA bypass, restricted sessions, credential/session theft, anti-bot evasion,
and residential proxy rotation are prohibited.
