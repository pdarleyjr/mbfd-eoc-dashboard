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

Acceptance requires successful Google script/tile loads, visible map controls,
no referrer rejection in the console, marker interaction, clustering, polygon
layers, and keyboard/touch-accessible layer toggles.
