import {Button, Checkbox, Tab, TabList} from '@fluentui/react-components'
import {Target20Regular} from '@fluentui/react-icons'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import {useEffect, useMemo, useRef, useState} from 'react'
import {useRadarStatus} from '../hooks/useRadarStatus'
import {
  useDashboardStore,
  type LayerKey,
  type LayerPreset,
  type MapMode,
} from '../store/dashboardStore'
import type {CanonicalRecord} from '../types'
import {filterVisibleRecords} from './map/layers'
import {windowedRadarFrames} from './map/radar'
import {RadarControls} from './map/RadarControls'

const mapTileUrl =
  (import.meta.env.VITE_MAP_TILE_URL as string | undefined)?.trim() ||
  'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const kioskResetMinutes = Math.max(1, Number(import.meta.env.VITE_RADAR_KIOSK_RESET_MINUTES ?? 10))

const modeLabels: ReadonlyArray<[MapMode, string]> = [
  ['operations', 'Operations'],
  ['radar', 'Radar'],
  ['flooding', 'Flooding'],
  ['tropical', 'Tropical'],
]

const layerGroups: ReadonlyArray<{
  name: string
  layers: ReadonlyArray<[LayerKey, string]>
}> = [
  {
    name: 'Operations',
    layers: [
      ['pulsepoint', 'PulsePoint advisory calls'],
      ['traffic', 'Traffic incidents'],
      ['laneClosures', 'Lane closures'],
    ],
  },
  {
    name: 'Weather',
    layers: [
      ['radar', 'MRMS radar'],
      ['alerts', 'Weather alerts'],
      ['outlooks', 'Day 1 outlooks'],
    ],
  },
  {
    name: 'Hazards',
    layers: [
      ['flood', 'Flood zones'],
      ['evacuation', 'Evacuation zones'],
      ['tropical', 'Current tropical products'],
      ['boundaries', 'Miami Beach boundary'],
    ],
  },
  {
    name: 'Resources',
    layers: [
      ['shelters', 'Shelters and centers'],
      ['facilities', 'Hospitals and hotels'],
      ['pumps', 'Stormwater pump assets'],
      ['transit', 'Transit routes and stops'],
    ],
  },
]

const presets: ReadonlyArray<[LayerPreset, string]> = [
  ['normal', 'Normal Operations'],
  ['severe', 'Severe Weather'],
  ['flooding', 'Flooding'],
  ['tropical', 'Tropical Activation'],
  ['evacuation', 'Evacuation'],
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
        : record.category === 'excessive_rainfall_outlook'
          ? '#187a4a'
          : record.category === 'severe_weather_outlook'
            ? '#d17a00'
            : record.category === 'tropical'
              ? '#9a3d8f'
              : record.authority_level === 'supplemental'
                ? '#6f45a8'
                : '#1769c2'
  return {
    pane: 'featurePane',
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

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : []
}

function RadarLayer({map, enabled}: {map: L.Map | null; enabled: boolean}) {
  const query = useRadarStatus(enabled)
  const record = query.data?.records[0]
  const frames = useMemo(() => stringArray(record?.payload.frame_times), [record])
  const [windowMinutes, setWindowMinutes] = useState(60)
  const [selectedFrame, setSelectedFrame] = useState<string>()
  const [playing, setPlaying] = useState(false)
  const [opacity, setOpacity] = useState(0.72)
  const activeLayer = useRef<L.TileLayer.WMS | null>(null)
  const preloadLayer = useRef<L.TileLayer.WMS | null>(null)

  const windowedFrames = useMemo(
    () => windowedRadarFrames(frames, windowMinutes),
    [frames, windowMinutes],
  )
  const latestFrame = windowedFrames.at(-1)
  const currentIndex = selectedFrame ? windowedFrames.indexOf(selectedFrame) : -1
  const nextFrame =
    playing && windowedFrames.length > 1
      ? windowedFrames[(Math.max(0, currentIndex) + 1) % windowedFrames.length]
      : undefined

  useEffect(() => {
    if (!playing || windowedFrames.length < 2) return
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (reducedMotion.matches) return
    const timer = window.setInterval(() => {
      if (document.hidden) return
      setSelectedFrame((current) => {
        const index = current ? windowedFrames.indexOf(current) : -1
        return windowedFrames[(index + 1 + windowedFrames.length) % windowedFrames.length]
      })
    }, 500)
    return () => window.clearInterval(timer)
  }, [playing, windowedFrames])

  useEffect(() => {
    if (!playing || !latestFrame) return
    let timer: number | undefined
    const scheduleReset = () => {
      if (timer !== undefined) window.clearTimeout(timer)
      timer = undefined
      if (!document.fullscreenElement) return
      timer = window.setTimeout(() => {
        setPlaying(false)
        setSelectedFrame(latestFrame)
      }, kioskResetMinutes * 60_000)
    }
    scheduleReset()
    document.addEventListener('fullscreenchange', scheduleReset)
    return () => {
      document.removeEventListener('fullscreenchange', scheduleReset)
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [latestFrame, playing])

  useEffect(() => {
    const displayedFrame = selectedFrame ?? latestFrame
    if (!map || !enabled || !displayedFrame) {
      activeLayer.current?.remove()
      activeLayer.current = null
      preloadLayer.current?.remove()
      preloadLayer.current = null
      return
    }
    const serviceUrl =
      typeof record?.payload.service_url === 'string'
        ? record.payload.service_url
        : 'https://nowcoast.noaa.gov/geoserver/observations/weather_radar/wms'
    const layerName =
      typeof record?.payload.layer_name === 'string'
        ? record.payload.layer_name
        : 'conus_base_reflectivity_mosaic'
    const options = {
      layers: layerName,
      format: 'image/png',
      transparent: true,
      opacity,
      pane: 'radarPane',
      time: displayedFrame,
      attribution: 'NOAA nowCOAST MRMS',
    } as L.WMSOptions & {time: string}
    activeLayer.current?.remove()
    activeLayer.current = L.tileLayer.wms(serviceUrl, options).addTo(map)

    preloadLayer.current?.remove()
    preloadLayer.current = null
    if (nextFrame && nextFrame !== displayedFrame) {
      const preloadOptions = {
        ...options,
        opacity: 0,
        time: nextFrame,
      } as L.WMSOptions & {time: string}
      preloadLayer.current = L.tileLayer.wms(serviceUrl, preloadOptions).addTo(map)
    }
    return () => {
      activeLayer.current?.remove()
      activeLayer.current = null
      preloadLayer.current?.remove()
      preloadLayer.current = null
    }
  }, [enabled, latestFrame, map, nextFrame, opacity, record, selectedFrame])

  if (!enabled) return null
  return (
    <RadarControls
      selectedFrame={selectedFrame ?? latestFrame}
      playing={playing}
      windowMinutes={windowMinutes}
      opacity={opacity}
      unavailable={
        query.isError ||
        query.data?.metadata.source_health === 'unavailable' ||
        query.data?.metadata.source_health === 'invalid_response' ||
        (!query.isLoading && !record)
      }
      legendUrl={
        typeof record?.payload.legend_url === 'string' ? record.payload.legend_url : undefined
      }
      onTogglePlaying={() => {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
        setPlaying((current) => !current)
      }}
      onLatest={() => {
        setPlaying(false)
        setSelectedFrame(latestFrame)
      }}
      onWindowChange={(minutes) => {
        setPlaying(false)
        setWindowMinutes(minutes)
        setSelectedFrame(undefined)
      }}
      onOpacityChange={setOpacity}
    />
  )
}

function LeafletMap({
  records,
  selectedRecordId,
  onSelect,
  mapMode,
}: {
  records: CanonicalRecord[]
  selectedRecordId: string | null
  onSelect: (id: string) => void
  mapMode: MapMode
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [map, setMap] = useState<L.Map | null>(null)
  const [tilesLoaded, setTilesLoaded] = useState(false)
  const [tileError, setTileError] = useState(false)
  const featureLayerRef = useRef<L.LayerGroup | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    const instance = L.map(containerRef.current, {
      attributionControl: true,
      keyboard: true,
      preferCanvas: false,
      zoomControl: false,
    }).setView([25.7907, -80.13], 12)
    instance.createPane('radarPane').style.zIndex = '250'
    instance.createPane('featurePane').style.zIndex = '410'
    L.control.zoom({position: 'topright'}).addTo(instance)
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
      .addTo(instance)
    const resize = () => window.requestAnimationFrame(() => instance.invalidateSize({pan: false}))
    const observer = new ResizeObserver(resize)
    observer.observe(containerRef.current)
    window.addEventListener('resize', resize)
    document.addEventListener('fullscreenchange', resize)
    setMap(instance)
    resize()
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', resize)
      document.removeEventListener('fullscreenchange', resize)
      tileLayer.off()
      instance.remove()
      setMap(null)
    }
  }, [])

  useEffect(() => {
    if (!map) return
    map.setView([25.7907, -80.13], mapMode === 'radar' ? 10 : 12)
  }, [map, mapMode])

  useEffect(() => {
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
        const marker = L.marker([position.lat, position.lng], {
          pane: 'featurePane',
          icon: L.divIcon({
            className: `leaflet-record-marker marker-${record.authority_level}${
              selected ? ' is-selected' : ''
            }`,
            html: `<span aria-hidden="true"><b>${markerGlyph(record)}</b></span>`,
            iconAnchor: [22, 42],
            iconSize: [44, 44],
          }),
          keyboard: true,
          riseOnHover: true,
          title: `${record.title}, ${record.source_name}`,
        }).on('click', () => onSelect(record.id))
        marker.on('add', () => {
          marker.getElement()?.setAttribute('aria-label', `${record.title}, ${record.source_name}`)
        })
        clusters.addLayer(marker)
        continue
      }
      if (!record.geography.type) continue
      try {
        const selected = record.id === selectedRecordId
        const feature: GeoJSON.Feature = {
          type: 'Feature',
          properties: {id: record.id, title: record.title},
          geometry: record.geography as unknown as GeoJSON.Geometry,
        }
        const shape = L.geoJSON(feature, {
          pane: 'featurePane',
          style: () => shapeStyle(record, selected),
          onEachFeature: (_feature, layer) => {
            const select = () => onSelect(record.id)
            layer.on('click', select)
            layer.on('add', () => makeShapeAccessible(layer, record, select))
          },
        }).addTo(allFeatures)
        if (selected) selectedShapes.push(shape)
      } catch {
        // Source health reports invalid geometry without taking down the operational map.
      }
    }
    const selectedRecord = records.find((record) => record.id === selectedRecordId)
    const selectedPoint = selectedRecord ? pointOf(selectedRecord) : null
    if (selectedPoint) {
      map.setView([selectedPoint.lat, selectedPoint.lng], Math.max(map.getZoom(), 15))
    } else if (selectedShapes[0]) {
      const bounds = selectedShapes[0].getBounds()
      if (bounds.isValid()) map.fitBounds(bounds, {maxZoom: 15, padding: [36, 36]})
    }
    return () => {
      allFeatures.remove()
      if (featureLayerRef.current === allFeatures) featureLayerRef.current = null
    }
  }, [map, onSelect, records, selectedRecordId])

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
            ? 'Configured basemap tiles are temporarily unavailable'
            : 'Loading configured basemap…'}
        </div>
      )}
      {mapMode === 'radar' && <RadarLayer map={map} enabled />}
      <QuickFocusControls onFocus={(lat, lng, zoom) => map?.setView([lat, lng], zoom)} />
    </div>
  )
}

export function OperationalMap({records}: {records: CanonicalRecord[]}) {
  const layers = useDashboardStore((state) => state.layers)
  const mapMode = useDashboardStore((state) => state.mapMode)
  const toggleLayer = useDashboardStore((state) => state.toggleLayer)
  const setMapMode = useDashboardStore((state) => state.setMapMode)
  const applyLayerPreset = useDashboardStore((state) => state.applyLayerPreset)
  const selectRecord = useDashboardStore((state) => state.selectRecord)
  const selectedRecordId = useDashboardStore((state) => state.selectedRecordId)
  const visible = useMemo(() => filterVisibleRecords(records, layers), [layers, records])

  return (
    <section className="panel map-panel" aria-labelledby="operational-map-heading">
      <div className="panel-title-row map-title-row">
        <div>
          <h2 id="operational-map-heading">Operational Map</h2>
          <p>Miami Beach, access corridors, and official hazard products</p>
        </div>
        <TabList
          className="map-mode-tabs"
          selectedValue={mapMode}
          onTabSelect={(_, data) => setMapMode(data.value as MapMode)}
          aria-label="Map mode"
          size="small"
        >
          {modeLabels.map(([value, label]) => (
            <Tab key={value} value={value}>
              {label}
            </Tab>
          ))}
        </TabList>
      </div>
      <div className="map-stage">
        <aside className="layer-list" aria-label="Map layers">
          <details className="layer-presets">
            <summary>Operational presets</summary>
            <div>
              {presets.map(([value, label]) => (
                <Button
                  key={value}
                  size="small"
                  appearance="subtle"
                  onClick={() => applyLayerPreset(value)}
                >
                  {label}
                </Button>
              ))}
            </div>
          </details>
          {layerGroups.map((group) => (
            <details key={group.name} open>
              <summary>{group.name}</summary>
              <div>
                {group.layers.map(([key, label]) => (
                  <Checkbox
                    key={key}
                    checked={layers[key]}
                    label={label}
                    onChange={() => toggleLayer(key)}
                  />
                ))}
              </div>
            </details>
          ))}
          <span className="authority-legend" aria-label="Map authority legend">
            <i className="legend-authoritative" /> Authoritative
            <i className="legend-advisory" /> Advisory
            <i className="legend-supplemental" /> Supplemental
          </span>
        </aside>
        <LeafletMap
          records={visible}
          selectedRecordId={selectedRecordId}
          onSelect={selectRecord}
          mapMode={mapMode}
        />
      </div>
    </section>
  )
}
