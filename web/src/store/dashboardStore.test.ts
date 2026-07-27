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
})
