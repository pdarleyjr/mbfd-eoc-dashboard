import {expect, it} from 'vitest'
import type {CanonicalRecord} from '../../types'
import {filterVisibleRecords} from './layers'

const baseRecord: CanonicalRecord = {
  id: 'record',
  source_id: 'source',
  source_name: 'Official source',
  source_type: 'official_api',
  authority_level: 'authoritative',
  source_record_id: 'record',
  source_url: 'https://example.gov',
  title: 'Record',
  category: 'traffic_incident',
  observed_at: '2026-07-29T12:00:00Z',
  published_at: null,
  retrieved_at: '2026-07-29T12:00:00Z',
  expires_at: null,
  stale: false,
  stale_reason: null,
  confidence: 1,
  geography: {},
  zip_scope: [],
  raw_snapshot_hash: 'a'.repeat(64),
  schema_version: 1,
  payload: {},
}

it('excludes unknown record categories instead of assigning them to traffic', () => {
  const records = [
    baseRecord,
    {...baseRecord, id: 'unknown', category: 'radar_status'},
    {...baseRecord, id: 'outlook', category: 'excessive_rainfall_outlook'},
  ]

  const visible = filterVisibleRecords(records, {
    pulsepoint: true,
    traffic: true,
    trafficCameras: true,
    laneClosures: true,
    radar: false,
    alerts: true,
    outlooks: true,
    flood: false,
    evacuation: false,
    shelters: true,
    facilities: true,
    pumps: false,
    transit: false,
    tropical: true,
    boundaries: true,
  })

  expect(visible.map((record) => record.id)).toEqual(['record', 'outlook'])
})

it('exposes official FL511 traffic cameras only when their map layer is enabled', () => {
  const camera = {...baseRecord, id: 'camera', category: 'traffic_camera'}
  const layers = {
    pulsepoint: true,
    traffic: true,
    trafficCameras: false,
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

  expect(filterVisibleRecords([camera], layers)).toEqual([])
  expect(filterVisibleRecords([camera], {...layers, trafficCameras: true})).toEqual([camera])
})
