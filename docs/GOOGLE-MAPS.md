# Google Maps

The browser integration uses `@vis.gl/react-google-maps`, Advanced Markers, and
marker clustering. Default center is `25.7907,-80.1300`; quick-focus controls
cover MacArthur, Julia Tuttle, and Venetian Causeways.

Build inputs:

```text
VITE_GOOGLE_MAPS_API_KEY
VITE_GOOGLE_MAPS_MAP_ID
```

The API key is a browser identifier, not a server secret, and must be restricted
to the Maps JavaScript API and approved HTTP referrers, including:

```text
https://eoc.mbfdhub.com/*
```

Preserve existing approved referrers when adding the EOC hostname. Never place a
server credential in a `VITE_*` value. When either value is absent, the UI shows a
clear configuration error and leaves operational lists available.

## 2026-07-28 authorization audit

A controlled browser probe of the browser key embedded in the current MBFD
Command build returned `RefererNotAllowedMapError` on both the Command and EOC
production origins. The Command build also had no production Map ID. That key
must not be copied into EOC as-is.

Use a dedicated EOC Websites-restricted browser key, authorize
`https://eoc.mbfdhub.com/*`, restrict it to Maps JavaScript API, confirm billing,
and create a production JavaScript vector Map ID. `DEMO_MAP_ID` is acceptable for
development diagnostics only. Vite values are image build inputs, so rebuild and
redeploy after changing them.

Acceptance requires successful Google script/tile loads, visible map controls,
no referrer rejection in the console, marker interaction, clustering, polygon
layers, and keyboard/touch-accessible layer toggles.
