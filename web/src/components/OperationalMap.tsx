import {MarkerClusterer} from '@googlemaps/markerclusterer'
import {APIProvider, Map as GoogleMap, useMap} from '@vis.gl/react-google-maps'
import {useEffect, useMemo} from 'react'
import {Checkbox, Button} from '@fluentui/react-components'
import {Location24Regular, Target20Regular} from '@fluentui/react-icons'
import type {CanonicalRecord} from '../types'
import {useDashboardStore, type LayerKey} from '../store/dashboardStore'

const mapKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined
const mapId = import.meta.env.VITE_GOOGLE_MAPS_MAP_ID as string | undefined

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

function ClusteredPoints({
  records,
  onSelect,
}: {
  records: CanonicalRecord[]
  onSelect: (id: string) => void
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
      markerButton.className = `map-marker marker-${record.authority_level} category-${record.category}`
      markerButton.setAttribute('aria-label', `${record.title}, ${record.source_name}`)
      markerButton.textContent =
        record.category === 'pulsepoint_call'
          ? '!'
          : record.category === 'open_shelter'
            ? 'S'
            : record.category === 'hospital'
              ? 'H'
              : '•'
      markerButton.addEventListener('click', () => onSelect(record.id))
      markers.push(
        new google.maps.marker.AdvancedMarkerElement({
          map,
          position,
          content: markerButton,
          title: record.title,
        }),
      )
    }
    const clusterer = new MarkerClusterer({map, markers})
    return () => {
      clusterer.clearMarkers()
      markers.forEach((marker) => {
        marker.map = null
      })
    }
  }, [map, onSelect, records])
  return null
}

function ShapeLayer({records}: {records: CanonicalRecord[]}) {
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
        strokeColor: category === 'lane_closure' ? '#c63d2f' : '#1769c2',
        strokeWeight: category === 'lane_closure' ? 4 : 2,
        fillColor: category === 'flood_zone' ? '#7eb6df' : '#6750a4',
        fillOpacity: 0.16,
      }
    })
    return () => map.data.forEach((feature: google.maps.Data.Feature) => map.data.remove(feature))
  }, [map, records])
  return null
}

function FocusControls() {
  const map = useMap()
  const focus = (lat: number, lng: number, zoom: number) => {
    map?.panTo({lat, lng})
    map?.setZoom(zoom)
  }
  return (
    <div className="causeway-focus" aria-label="Causeway quick focus">
      <Button size="small" appearance="subtle" onClick={() => focus(25.782, -80.163, 14)}>
        MacArthur
      </Button>
      <Button size="small" appearance="subtle" onClick={() => focus(25.811, -80.162, 14)}>
        Julia Tuttle
      </Button>
      <Button size="small" appearance="subtle" onClick={() => focus(25.7905, -80.166, 14)}>
        Venetian
      </Button>
      <Button
        size="small"
        appearance="subtle"
        icon={<Target20Regular />}
        aria-label="Reset map to Miami Beach"
        onClick={() => focus(25.7907, -80.13, 12)}
      />
    </div>
  )
}

export function OperationalMap({records}: {records: CanonicalRecord[]}) {
  const layers = useDashboardStore((state) => state.layers)
  const toggleLayer = useDashboardStore((state) => state.toggleLayer)
  const selectRecord = useDashboardStore((state) => state.selectRecord)
  const visible = useMemo(
    () => records.filter((record) => layers[categoryLayer[record.category] ?? 'traffic']),
    [layers, records],
  )

  return (
    <section className="panel map-panel" aria-labelledby="operational-map-heading">
      <div className="panel-title-row map-title-row">
        <div>
          <h2 id="operational-map-heading">Operational Map</h2>
          <p>Miami Beach, access corridors, and relevant public-source features</p>
        </div>
        <span className="authority-legend">
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
        {!mapKey || !mapId ? (
          <div className="map-config-error" role="status">
            <Location24Regular aria-hidden />
            <strong>Google Maps configuration is unavailable</strong>
            <span>
              Set the referrer-restricted browser key and Map ID. Operational lists remain
              available.
            </span>
          </div>
        ) : (
          <APIProvider apiKey={mapKey} libraries={['marker']}>
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
              <ClusteredPoints records={visible} onSelect={selectRecord} />
              <ShapeLayer records={visible} />
              <FocusControls />
            </GoogleMap>
          </APIProvider>
        )}
      </div>
    </section>
  )
}
