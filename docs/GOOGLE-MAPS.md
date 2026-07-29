# Operational map

Leaflet 1.9.4 is the single production map renderer. It uses the Miami Beach
center `25.7907,-80.1300`, point clustering, official GeoJSON point/line/polygon
features, selected-feature highlighting, keyboard-accessible shape interaction,
and quick focus for the MacArthur, Julia Tuttle, and Venetian Causeways.

Build inputs:

```text
VITE_MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
VITE_RADAR_KIOSK_RESET_MINUTES=10
```

The tile URL is compiled into the SPA and can be replaced by an approved
operator-hosted tile service without changing application code. Any replacement
host must also be explicitly allowed by the production Content Security Policy.

The public OpenStreetMap service is used only for ordinary interactive browser
tiles with its exact HTTPS URL, visible attribution, normal browser
headers/caching, and no bulk download or prefetch. It has no availability SLA;
an approved provider or self-hosted tiles are required when an SLA is needed.
The map reports tile failures without obscuring operational features.

NOAA nowCOAST MRMS base reflectivity is a separate time-aware WMS layer beneath
operational features. The API reads the service capability document and returns
the exact frame list. The browser starts at the latest frame without animation,
requests only the selected frame, and preloads only the next frame during
operator-initiated playback. Playback uses 500 ms steps, pauses while the page is
hidden, respects reduced-motion settings, and returns a full-screen kiosk to the
latest frame after the configured interval.

Acceptance requires successful configured basemap and radar tile responses,
visible attribution and source age, working zoom/causeway controls, clustered
and selected points, keyboard activation of lines/polygons, map-mode and layer
controls through pointer or keyboard input, and resize/full-screen reflow.
