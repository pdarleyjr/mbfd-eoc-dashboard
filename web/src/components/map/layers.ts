import type {LayerKey} from '../../store/dashboardStore'
import type {CanonicalRecord} from '../../types'

export const categoryLayer: Readonly<Record<string, LayerKey>> = {
  pulsepoint_call: 'pulsepoint',
  traffic_incident: 'traffic',
  lane_closure: 'laneClosures',
  weather_alert: 'alerts',
  excessive_rainfall_outlook: 'outlooks',
  severe_weather_outlook: 'outlooks',
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

export function filterVisibleRecords(
  records: CanonicalRecord[],
  layers: Record<LayerKey, boolean>,
): CanonicalRecord[] {
  return records.filter((record) => {
    const layer = categoryLayer[record.category]
    return layer ? layers[layer] : false
  })
}
