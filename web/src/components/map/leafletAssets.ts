import L from 'leaflet'
import markerIconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import markerIconUrl from 'leaflet/dist/images/marker-icon.png'
import markerShadowUrl from 'leaflet/dist/images/marker-shadow.png'

export const leafletDefaultIconAssets = {
  iconRetinaUrl: markerIconRetinaUrl,
  iconUrl: markerIconUrl,
  shadowUrl: markerShadowUrl,
}

export function configureLeafletDefaultIconAssets() {
  L.Icon.Default.mergeOptions(leafletDefaultIconAssets)
}
