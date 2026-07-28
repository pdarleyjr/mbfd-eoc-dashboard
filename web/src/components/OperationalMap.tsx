import {MarkerClusterer} from '@googlemaps/markerclusterer'
import {APIProvider, Map as GoogleMap, useMap} from '@vis.gl/react-google-maps'
import {Button, Checkbox} from '@fluentui/react-components'
import {Target20Regular} from '@fluentui/react-icons'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import {useEffect, useMemo, useRef, useState} from 'react'
import {useDashboardStore, type LayerKey} from '../store/dashboardStore'
import type {CanonicalRecord} from '../types'

const mapKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined
const mapId = import.meta.env.VITE_GOOGLE_MAPS_MAP_ID as string | undefined
const mapTileUrl =
  (import.meta.env.VITE_MAP_TILE_URL as string | undefined)?.trim() ||
  'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

declare global {
  interface Window {
    gm_authFailure?: () => void
  }
}

const categoryLayer: Record<string, LayerKey> = {
  pulsepoint_call: 'pulsepoint',
  traffic_incident: 'traffic',
  lane_closure: 'laneClosures',
  weather_alert: 'weather',
  flood_zone: 'flood',
  evacuation_zone: 'evacuation',
  open_shelter: 'shelters',
  evacuation_center: 'shelters',
  hospital: 'facilities',
  hotel: 'facilities',
  stormwater_pump_asset: 'pumps',
  transit: 'transit',
  tropical: 'tropical',
  municipal_boundary: 'boundaries',
}

const layerLabels: Array<[LayerKey, string]> = [
  ['pulsepoint', 'PulsePoint advisory calls'],
  ['traffic', 'Traffic incidents'],
  ['laneClosures', 'Lane closures'],
  ['weather', 'Weather alerts'],
  ['flood', 'Flood zones'],
  ['evacuation', 'Evacuation zones'],
  ['shelters', 'Shelters and centers'],
  ['facilities', 'Hospitals and hotels'],
  ['pumps', 'Stormwater pump assets'],
  ['transit', 'Transit routes and stops'],
  ['tropical', 'Current tropical products'],
  ['boundaries', 'Miami Beach boundary'],
]

function pointOf(record: CanonicalRecord): {lat: number; lng: number} | null {
  const coordinates = record.geography.coordinates
  if (
    record.geography.type !== 'Point' ||
    !Array.isArray(coordinates) ||
    typeof coordinates[0] !== 'number' ||
    typeof coordinates[1] !== 'number'
  )
    return null
  return {lng: coordinates[0], lat: coordinates[1]}
}

function visibleRecords(
  records: CanonicalRecord[],
  layers: Record<LayerKey, boolean>,
): CanonicalRecord[] {
  return records.filter((record) => layers[categoryLayer[record.category] ?? 'traffic'])
}

function markerGlyph(record: CanonicalRecord): string {
  if (record.category === 'pulsepoint_call') return '!'
  if (record.category === 'open_shelter' || record.category === 'evacuation_center') return 'S'
  if (record.category === 'hospital') return 'H'
  if (record.category === 'hotel') return 'L'
  return '•'
}

function shapeStyle(record: CanonicalRecord, selected: boolean): L.PathOptions {
  const strokeColor =
    record.category === 'lane_closure'
      ? '#b72b29'
      : record.category === 'evacuation_zone'
        ? '#6750a4'
        : record.authority_level === 'supplemental'
          ? '#6f45a8'
          : '#1769c2'
  return {
    color: strokeColor,
    weight: selected ? 6 : record.category === 'lane_closure' ? 4 : 2,
    opacity: 0.92,
    fillColor:
      record.category === 'flood_zone'
        ? '#4b9bd5'
        : record.category === 'evacuation_zone'
          ? '#8064b0'
          : strokeColor,
    fillOpacity: record.category === 'municipal_boundary' ? 0.04 : 0.18,
  }
}

function makeShapeAccessible(layer: L.Layer, record: CanonicalRecord, onSelect: () => void) {
  if (!(layer instanceof L.Path)) return
  const element = layer.getElement()
  if (!element) return
  element.setAttribute('role', 'button')
  element.setAttribute('tabindex', '0')
  element.setAttribute('aria-label', `${record.title}, ${record.source_name}`)
  element.addEventListener('keydown', (event) => {
    const keyboardEvent = event as KeyboardEvent
    if (keyboardEvent.key !== 'Enter' && keyboardEvent.key !== ' ') return
    keyboardEvent.preventDefault()
    onSelect()
  })
}

function QuickFocusControls({
  onFocus,
}: {
  onFocus: (lat: number, lng: number, zoom: number) => void
}) {
  return (
    <div className="causeway-focus" aria-label="Causeway quick focus">
      <Button size="small" appearance="subtle" onClick={() => onFocus(25.782, -80.163, 14)}>
        MacArthur
      </Button>
      <Button size="small" appearance="subtle" onClick={() => onFocus(25.811, -80.162, 14)}>
        Julia Tuttle
      </Button>
      <Button size="small" appearance="subtle" onClick={() => onFocus(25.7905, -80.166, 14)}>
        Venetian
      </Button>
      <Button
        size="small"
        appearance="subtle"
        icon={<Target20Regular />}
        aria-label="Reset map to Miami Beach"
        onClick={() => onFocus(25.7907, -80.13, 12)}
      />
    </div>
  )
}

function LeafletFallback({
  records,
  onSelect,
  selectedRecordId,
}: {
  records: CanonicalRecord[]
  onSelect: (id: string) => void
  selectedRecordId: string | null
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const featureLayerRef = useRef<L.LayerGroup | null>(null)
  const [tilesLoaded, setTilesLoaded] = useState(false)
  const [tileError, setTileError] = useState(false)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const map = L.map(containerRef.current, {
      attributionControl: true,
      keyboard: true,
      preferCanvas: false,
      zoomControl: false,
    }).setView([25.7907, -80.13], 12)
    mapRef.current = map
    L.control.zoom({position: 'topright'}).addTo(map)
    const tileLayer = L.tileLayer(mapTileUrl, {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
      maxZoom: 19,
    })
      .on('load', () => {
        setTilesLoaded(true)
        setTileError(false)
      })
      .on('tileerror', () => setTileError(true))
      .addTo(map)

    const resize = () => window.requestAnimationFrame(() => map.invalidateSize({pan: false}))
    const observer = new ResizeObserver(resize)
    observer.observe(containerRef.current)
    window.addEventListener('resize', resize)
    document.addEventListener('fullscreenchange', resize)
    resize()

    return () => {
      observer.disconnect()
      window.removeEventListener('resize', resize)
      document.removeEventListener('fullscreenchange', resize)
      tileLayer.off()
      map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    featureLayerRef.current?.remove()

    const allFeatures = L.layerGroup().addTo(map)
    featureLayerRef.current = allFeatures
    const clusters = L.markerClusterGroup({
      chunkedLoading: true,
      disableClusteringAtZoom: 15,
      maxClusterRadius: 48,
      showCoverageOnHover: false,
      iconCreateFunction: (cluster) =>
        L.divIcon({
          className: 'leaflet-cluster-marker',
          html: `<span>${cluster.getChildCount()}</span>`,
          iconAnchor: [22, 22],
          iconSize: [44, 44],
        }),
    }).addTo(allFeatures)
    const selectedShapes: L.GeoJSON[] = []

    for (const record of records) {
      const position = pointOf(record)
      if (position) {
        const selected = record.id === selectedRecordId
        const icon = L.divIcon({
          className: `leaflet-record-marker marker-${record.authority_level}${
            selected ? ' is-selected' : ''
          }`,
          html: `<span aria-hidden="true"><b>${markerGlyph(record)}</b></span>`,
          iconAnchor: [22, 42],
          iconSize: [44, 44],
        })
        const marker = L.marker([position.lat, position.lng], {
          icon,
          keyboard: true,
          riseOnHover: true,
          title: `${record.title}, ${record.source_name}`,
        }).on('click', () => onSelect(record.id))
        marker.on('add', () => {
          const element = marker.getElement()
          element?.setAttribute('role', 'button')
          element?.setAttribute('aria-label', `${record.title}, ${record.source_name}`)
        })
        clusters.addLayer(marker)
        continue
      }
      if (!record.geography.type) continue
      try {
        const selected = record.id === selectedRecordId
        const feature: GeoJSON.Feature = {
          type: 'Feature',
          properties: {
            id: record.id,
            title: record.title,
            authority: record.authority_level,
            category: record.category,
          },
          geometry: record.geography as unknown as GeoJSON.Geometry,
        }
        const shape = L.geoJSON(feature, {
          style: () => shapeStyle(record, selected),
          onEachFeature: (_feature, layer) => {
            const select = () => onSelect(record.id)
            layer.on('click', select)
            layer.on('add', () => makeShapeAccessible(layer, record, select))
          },
        }).addTo(allFeatures)
        if (selected) selectedShapes.push(shape)
      } catch {
        // Invalid source geometry stays visible in source health instead of breaking the map.
      }
    }

    const selectedRecord = records.find((record) => record.id === selectedRecordId)
    const selectedPoint = selectedRecord ? pointOf(selectedRecord) : null
    if (selectedPoint) {
      map.setView([selectedPoint.lat, selectedPoint.lng], Math.max(map.getZoom(), 15))
    } else {
      const selectedShape = selectedShapes[0]
      if (selectedShape) {
        const bounds = selectedShape.getBounds()
        if (bounds.isValid()) map.fitBounds(bounds, {maxZoom: 15, padding: [36, 36]})
      }
    }

    return () => {
      allFeatures.remove()
      if (featureLayerRef.current === allFeatures) featureLayerRef.current = null
    }
  }, [onSelect, records, selectedRecordId])

  const focus = (lat: number, lng: number, zoom: number) => {
    mapRef.current?.setView([lat, lng], zoom)
  }

  return (
    <div className="leaflet-fallback">
      <div
        ref={containerRef}
        className="leaflet-map"
        role="region"
        aria-label="Miami Beach operational map"
        aria-busy={!tilesLoaded}
      />
      {!tilesLoaded && (
        <div className={`map-loading-overlay${tileError ? ' map-tile-error' : ''}`} role="status">
          {tileError
            ? 'OpenStreetMap basemap tiles are temporarily unavailable'
            : 'Loading OpenStreetMap basemap…'}
        </div>
      )}
      <QuickFocusControls onFocus={focus} />
    </div>
  )
}

function ClusteredPoints({
  records,
  onSelect,
  selectedRecordId,
}: {
  records: CanonicalRecord[]
  onSelect: (id: string) => void
  selectedRecordId: string | null
}) {
  const map = useMap()
  useEffect(() => {
    if (!map || !window.google?.maps?.marker) return
    const markers: google.maps.marker.AdvancedMarkerElement[] = []
    for (const record of records) {
      const position = pointOf(record)
      if (!position) continue
      const markerButton = document.createElement('button')
      markerButton.type = 'button'
      markerButton.className = `map-marker marker-${record.authority_level} category-${
        record.category
      }${record.id === selectedRecordId ? ' is-selected' : ''}`
      markerButton.setAttribute('aria-label', `${record.title}, ${record.source_name}`)
      markerButton.textContent = markerGlyph(record)
      markerButton.addEventListener('click', () => onSelect(record.id))
      const marker = new google.maps.marker.AdvancedMarkerElement({
        map,
        position,
        content: markerButton,
        title: record.title,
      })
      markers.push(marker)
      if (record.id === selectedRecordId) {
        map.panTo(position)
        map.setZoom(Math.max(map.getZoom() ?? 12, 15))
      }
    }
    const clusterer = new MarkerClusterer({map, markers})
    return () => {
      clusterer.clearMarkers()
      markers.forEach((marker) => {
        marker.map = null
      })
    }
  }, [map, onSelect, records, selectedRecordId])
  return null
}

function ShapeLayer({
  records,
  onSelect,
}: {
  records: CanonicalRecord[]
  onSelect: (id: string) => void
}) {
  const map = useMap()
  useEffect(() => {
    if (!map) return
    map.data.forEach((feature: google.maps.Data.Feature) => map.data.remove(feature))
    for (const record of records) {
      if (!record.geography.type || record.geography.type === 'Point') continue
      try {
        map.data.addGeoJson({
          type: 'Feature',
          id: record.id,
          properties: {
            title: record.title,
            authority: record.authority_level,
            category: record.category,
          },
          geometry: record.geography as unknown as GeoJSON.Geometry,
        })
      } catch {
        // Invalid source geometry stays visible in source health instead of breaking the map.
      }
    }
    map.data.setStyle((feature: google.maps.Data.Feature) => {
      const category = feature.getProperty('category') as string
      return {
        clickable: true,
        cursor: 'pointer',
        strokeColor:
          category === 'lane_closure'
            ? '#c63d2f'
            : category === 'evacuation_zone'
              ? '#6750a4'
              : '#1769c2',
        strokeWeight: category === 'lane_closure' ? 4 : 2,
        fillColor:
          category === 'flood_zone'
            ? '#4b9bd5'
            : category === 'evacuation_zone'
              ? '#8064b0'
              : '#1769c2',
        fillOpacity: category === 'municipal_boundary' ? 0.04 : 0.18,
      }
    })
    const clickListener = map.data.addListener('click', (event: google.maps.Data.MouseEvent) => {
      const id = event.feature.getId()
      if (typeof id === 'string') onSelect(id)
    })
    return () => {
      clickListener.remove()
      map.data.forEach((feature: google.maps.Data.Feature) => map.data.remove(feature))
    }
  }, [map, onSelect, records])
  return null
}

function GoogleFocusControls() {
  const map = useMap()
  const focus = (lat: number, lng: number, zoom: number) => {
    map?.panTo({lat, lng})
    map?.setZoom(zoom)
  }
  return <QuickFocusControls onFocus={focus} />
}

export function OperationalMap({records}: {records: CanonicalRecord[]}) {
  const [mapLoadFailed, setMapLoadFailed] = useState(false)
  const [mapLoaded, setMapLoaded] = useState(false)
  const layers = useDashboardStore((state) => state.layers)
  const toggleLayer = useDashboardStore((state) => state.toggleLayer)
  const selectRecord = useDashboardStore((state) => state.selectRecord)
  const selectedRecordId = useDashboardStore((state) => state.selectedRecordId)
  const visible = useMemo(() => visibleRecords(records, layers), [layers, records])

  useEffect(() => {
    if (!mapKey || !mapId) return
    const previous = window.gm_authFailure
    window.gm_authFailure = () => setMapLoadFailed(true)
    return () => {
      window.gm_authFailure = previous
    }
  }, [])

  return (
    <section className="panel map-panel" aria-labelledby="operational-map-heading">
      <div className="panel-title-row map-title-row">
        <div>
          <h2 id="operational-map-heading">Operational Map</h2>
          <p>Miami Beach, access corridors, and relevant public-source features</p>
        </div>
        <span className="authority-legend" aria-label="Map authority legend">
          <i className="legend-authoritative" /> Authoritative
          <i className="legend-advisory" /> Advisory
          <i className="legend-supplemental" /> Supplemental
        </span>
      </div>
      <div className="map-stage">
        <aside className="layer-list" aria-label="Map layers">
          <strong>Layers</strong>
          {layerLabels.map(([key, label]) => (
            <Checkbox
              key={key}
              checked={layers[key]}
              label={label}
              onChange={() => toggleLayer(key)}
            />
          ))}
        </aside>
        {!mapKey || !mapId || mapLoadFailed ? (
          <LeafletFallback
            records={visible}
            onSelect={selectRecord}
            selectedRecordId={selectedRecordId}
          />
        ) : (
          <APIProvider
            apiKey={mapKey}
            libraries={['marker']}
            onLoad={() => setMapLoaded(true)}
            onError={() => setMapLoadFailed(true)}
          >
            <GoogleMap
              defaultCenter={{lat: 25.7907, lng: -80.13}}
              defaultZoom={12}
              mapId={mapId}
              gestureHandling="greedy"
              disableDefaultUI
              zoomControl
              fullscreenControl={false}
              aria-label="Miami Beach operational map"
            >
              <ClusteredPoints
                records={visible}
                onSelect={selectRecord}
                selectedRecordId={selectedRecordId}
              />
              <ShapeLayer records={visible} onSelect={selectRecord} />
              <GoogleFocusControls />
            </GoogleMap>
            {!mapLoaded && (
              <div className="map-loading-overlay" role="status">
                Loading Google Maps…
              </div>
            )}
          </APIProvider>
        )}
      </div>
    </section>
  )
}
