import {beforeEach, describe, expect, it} from 'vitest'
import {useDashboardStore} from './dashboardStore'

describe('dashboard settings store', () => {
  beforeEach(() => useDashboardStore.getState().reset())

  it('toggles map layers through a click-accessible action', () => {
    useDashboardStore.getState().toggleLayer('shelters')
    expect(useDashboardStore.getState().layers.shelters).toBe(false)
  })

  it('supports compact and comfortable density', () => {
    useDashboardStore.getState().setDensity('comfortable')
    expect(useDashboardStore.getState().density).toBe('comfortable')
  })

  it('defaults to operations and applies the radar mode layer contract', () => {
    expect(useDashboardStore.getState().mapMode).toBe('operations')

    useDashboardStore.getState().setMapMode('radar')

    const state = useDashboardStore.getState()
    expect(state.mapMode).toBe('radar')
    expect(state.layers.radar).toBe(true)
    expect(state.layers.alerts).toBe(true)
    expect(state.layers.boundaries).toBe(true)
    expect(state.layers.pulsepoint).toBe(true)
    expect(state.layers.traffic).toBe(true)
    expect(state.layers.laneClosures).toBe(true)
    expect(state.layers.facilities).toBe(false)
    expect(state.layers.transit).toBe(false)
    expect(state.layers.pumps).toBe(false)
    expect(state.layers.evacuation).toBe(false)
  })

  it('applies named operational presets without disabling manual layer toggles', () => {
    useDashboardStore.getState().applyLayerPreset('evacuation')
    expect(useDashboardStore.getState().layers.evacuation).toBe(true)
    expect(useDashboardStore.getState().layers.shelters).toBe(true)
    expect(useDashboardStore.getState().layers.transit).toBe(true)
    expect(useDashboardStore.getState().layers.radar).toBe(false)

    useDashboardStore.getState().toggleLayer('radar')
    expect(useDashboardStore.getState().layers.radar).toBe(true)
  })
})
