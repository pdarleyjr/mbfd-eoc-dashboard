import {create} from 'zustand'

export type LayerKey =
  | 'pulsepoint'
  | 'traffic'
  | 'laneClosures'
  | 'weather'
  | 'flood'
  | 'evacuation'
  | 'shelters'
  | 'facilities'
  | 'pumps'
  | 'transit'
  | 'tropical'
  | 'boundaries'

type Density = 'compact' | 'comfortable'

const defaultLayers: Record<LayerKey, boolean> = {
  pulsepoint: true,
  traffic: true,
  laneClosures: true,
  weather: true,
  flood: false,
  evacuation: false,
  shelters: true,
  facilities: true,
  pumps: false,
  transit: false,
  tropical: true,
  boundaries: true,
}

interface DashboardStore {
  layers: Record<LayerKey, boolean>
  density: Density
  sourceDrawerOpen: boolean
  settingsOpen: boolean
  selectedRecordId: string | null
  toggleLayer: (layer: LayerKey) => void
  setDensity: (density: Density) => void
  setSourceDrawerOpen: (open: boolean) => void
  setSettingsOpen: (open: boolean) => void
  selectRecord: (recordId: string | null) => void
  reset: () => void
}

export const useDashboardStore = create<DashboardStore>((set) => ({
  layers: {...defaultLayers},
  density: 'compact',
  sourceDrawerOpen: false,
  settingsOpen: false,
  selectedRecordId: null,
  toggleLayer: (layer) =>
    set((state) => ({layers: {...state.layers, [layer]: !state.layers[layer]}})),
  setDensity: (density) => set({density}),
  setSourceDrawerOpen: (sourceDrawerOpen) => set({sourceDrawerOpen}),
  setSettingsOpen: (settingsOpen) => set({settingsOpen}),
  selectRecord: (selectedRecordId) => set({selectedRecordId}),
  reset: () =>
    set({
      layers: {...defaultLayers},
      density: 'compact',
      sourceDrawerOpen: false,
      settingsOpen: false,
      selectedRecordId: null,
    }),
}))
