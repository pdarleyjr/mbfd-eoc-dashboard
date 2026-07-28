# Operational maps

The dashboard always has a deployable keyless map. Leaflet 1.9.4 and
OpenStreetMap tiles are the production fallback; Google Maps remains an optional
enhancement. Both implementations use the Miami Beach center
`25.7907,-80.1300`, point clustering, authority/category symbology, clickable
point/line/polygon features, selected-feature highlighting, keyboard-accessible
shape interaction, and quick focus for MacArthur, Julia Tuttle, and Venetian
Causeways.

Build inputs:

```text
VITE_GOOGLE_MAPS_API_KEY
VITE_GOOGLE_MAPS_MAP_ID
VITE_MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
```

When the two Google values are absent, or when Google calls
`window.gm_authFailure`, the same lazy map chunk starts Leaflet automatically.
The tile URL is compiled into the SPA and can be replaced by an approved
operator-hosted tile service without changing application code.

The public OpenStreetMap service must be used in accordance with its tile usage
policy: keep the exact HTTPS URL, visible OpenStreetMap attribution, normal
browser referrer and user-agent headers, HTTP caching, and no bulk download or
prefetch. The public service has no availability SLA; organizations needing one
must configure a suitable provider or self-hosted tiles.

## Optional Google Maps configuration

The API key is a browser identifier, not a server secret, and must be restricted
to the Maps JavaScript API and approved HTTP referrers, including:

```text
https://eoc.mbfdhub.com/*
```

Preserve existing approved referrers when adding the EOC hostname. Never place a
server credential in a `VITE_*` value.

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

Google acceptance requires successful script/tile loads, visible controls, no
referrer rejection in the console, Advanced Marker interaction, clustering,
polygon layers, and keyboard/touch-accessible layer toggles. A Google
authorization failure is not allowed to remove the operational map; the Leaflet
fallback must become visible.

Keyless-fallback acceptance requires real OpenStreetMap tile responses, visible
street/area labels and attribution, a loading/error state that clears, working
zoom and causeway-focus controls, clustered and selected points, keyboard
activation of lines/polygons, and a successful resize/full-screen reflow.
