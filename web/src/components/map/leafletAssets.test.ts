import L from 'leaflet'
import {describe, expect, it} from 'vitest'
import {configureLeafletDefaultIconAssets, leafletDefaultIconAssets} from './leafletAssets'

describe('Leaflet default marker assets', () => {
  it('uses Vite-managed URLs instead of unresolved site-root filenames', () => {
    configureLeafletDefaultIconAssets()

    expect(L.Icon.Default.prototype.options.iconUrl).toBe(leafletDefaultIconAssets.iconUrl)
    expect(L.Icon.Default.prototype.options.iconRetinaUrl).toBe(
      leafletDefaultIconAssets.iconRetinaUrl,
    )
    expect(L.Icon.Default.prototype.options.shadowUrl).toBe(leafletDefaultIconAssets.shadowUrl)
    expect(
      Object.values(leafletDefaultIconAssets).every((url) => url.includes('/leaflet/dist/images/')),
    ).toBe(true)
  })
})
