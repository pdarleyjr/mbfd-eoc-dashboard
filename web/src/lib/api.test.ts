import {afterEach, describe, expect, it, vi} from 'vitest'
import type {DashboardSummary} from '../types'
import {fetchDashboard} from './api'

const SNAPSHOT_KEY = 'mbfd-eoc:last-rendered-dashboard:v2'
const generatedAt = '2026-08-01T20:00:00Z'

function dashboardSummary(): DashboardSummary {
  return {
    metadata: {
      generated_at: generatedAt,
      source_observation_time: generatedAt,
      data_age_seconds: 0,
      stale: false,
      source_authority: ['advisory'],
      source_health: 'healthy',
      last_successful_refresh: generatedAt,
      empty_state: null,
    },
    kpis: [],
    records: [
      {
        id: 'pulsepoint:current',
        source_id: 'pulsepoint-x1012',
        source_name: 'PulsePoint Miami Beach X1012',
        source_type: 'pulsepoint_advisory',
        authority_level: 'advisory',
        source_record_id: 'current',
        source_url: 'https://example.gov/pulsepoint',
        title: 'Medical Emergency',
        category: 'pulsepoint_call',
        observed_at: generatedAt,
        published_at: generatedAt,
        retrieved_at: generatedAt,
        expires_at: null,
        stale: false,
        stale_reason: null,
        confidence: 1,
        geography: {},
        zip_scope: [],
        raw_snapshot_hash: 'a'.repeat(64),
        schema_version: 1,
        payload: {state: 'active'},
      },
    ],
    source_health: [],
    health_summary: {
      critical_healthy: 1,
      critical_total: 1,
      all_healthy: 1,
      all_total: 1,
      unavailable_critical: [],
    },
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('fetchDashboard', () => {
  it('marks a service-worker cache hit and every cached record stale', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(dashboardSummary()), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            'X-EOC-Cache': 'hit',
          },
        }),
      ),
    )

    const result = await fetchDashboard()

    expect(result.metadata.stale).toBe(true)
    expect(result.metadata.source_health).toBe('stale')
    expect(result.metadata.empty_state).toBe(`Showing cached information from ${generatedAt}`)
    expect(result.records).toEqual([
      expect.objectContaining({
        stale: true,
        stale_reason: `Showing cached information from ${generatedAt}`,
      }),
    ])
    expect(localStorage.getItem(SNAPSHOT_KEY)).toBeNull()
  })

  it('stores and returns a fresh network response unchanged', async () => {
    const summary = dashboardSummary()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(summary), {
          status: 200,
          headers: {'Content-Type': 'application/json'},
        }),
      ),
    )

    await expect(fetchDashboard()).resolves.toEqual(summary)
    expect(JSON.parse(localStorage.getItem(SNAPSHOT_KEY) ?? 'null')).toEqual(summary)
  })
})
