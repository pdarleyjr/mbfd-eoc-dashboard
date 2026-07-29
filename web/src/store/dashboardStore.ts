import {create} from 'zustand'

export type LayerKey =
  | 'pulsepoint'
  | 'traffic'
  | 'laneClosures'
  | 'radar'
  | 'alerts'
  | 'outlooks'
  | 'flood'
  | 'evacuation'
  | 'shelters'
  | 'facilities'
  | 'pumps'
  | 'transit'
  | 'tropical'
  | 'boundaries'

export type MapMode = 'operations' | 'radar' | 'flooding' | 'tropical'
export type LayerPreset = 'normal' | 'severe' | 'flooding' | 'tropical' | 'evacuation'
type Density = 'compact' | 'comfortable'

const layerDefaults: Record<LayerKey, boolean> = {
  pulsepoint: true,
  traffic: true,
  laneClosures: true,
  radar: false,
  alerts: true,
  outlooks: false,
  flood: false,
  evacuation: false,
  shelters: true,
  facilities: true,
  pumps: false,
  transit: false,
  tropical: true,
  boundaries: true,
}

const modeLayers: Record<MapMode, Record<LayerKey, boolean>> = {
  operations: layerDefaults,
  radar: {
    ...layerDefaults,
    radar: true,
    outlooks: true,
    facilities: false,
    pumps: false,
    transit: false,
    evacuation: false,
  },
  flooding: {
    ...layerDefaults,
    alerts: true,
    outlooks: true,
    flood: true,
    pumps: true,
    facilities: false,
    transit: false,
  },
  tropical: {
    ...layerDefaults,
    radar: true,
    alerts: true,
    outlooks: true,
    evacuation: true,
    shelters: true,
    tropical: true,
    facilities: false,
  },
}

const presetLayers: Record<LayerPreset, Record<LayerKey, boolean>> = {
  normal: layerDefaults,
  severe: modeLayers.radar,
  flooding: modeLayers.flooding,
  tropical: modeLayers.tropical,
  evacuation: {
    ...layerDefaults,
    radar: false,
    alerts: true,
    outlooks: false,
    evacuation: true,
    shelters: true,
    transit: true,
    facilities: false,
    pumps: false,
  },
}

interface DashboardStore {
  layers: Record<LayerKey, boolean>
  mapMode: MapMode
  density: Density
  sourceDrawerOpen: boolean
  settingsOpen: boolean
  selectedRecordId: string | null
  toggleLayer: (layer: LayerKey) => void
  setMapMode: (mode: MapMode) => void
  applyLayerPreset: (preset: LayerPreset) => void
  setDensity: (density: Density) => void
  setSourceDrawerOpen: (open: boolean) => void
  setSettingsOpen: (open: boolean) => void
  selectRecord: (recordId: string | null) => void
  reset: () => void
}

export const useDashboardStore = create<DashboardStore>((set) => ({
  layers: {...layerDefaults},
  mapMode: 'operations',
  density: 'compact',
  sourceDrawerOpen: false,
  settingsOpen: false,
  selectedRecordId: null,
  toggleLayer: (layer) =>
    set((state) => ({layers: {...state.layers, [layer]: !state.layers[layer]}})),
  setMapMode: (mapMode) => set({mapMode, layers: {...modeLayers[mapMode]}}),
  applyLayerPreset: (preset) => set({layers: {...presetLayers[preset]}}),
  setDensity: (density) => set({density}),
  setSourceDrawerOpen: (sourceDrawerOpen) => set({sourceDrawerOpen}),
  setSettingsOpen: (settingsOpen) => set({settingsOpen}),
  selectRecord: (selectedRecordId) => set({selectedRecordId}),
  reset: () =>
    set({
      layers: {...layerDefaults},
      mapMode: 'operations',
      density: 'compact',
      sourceDrawerOpen: false,
      settingsOpen: false,
      selectedRecordId: null,
    }),
}))
