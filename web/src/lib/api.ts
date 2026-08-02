import {
  dashboardSummarySchema,
  recordsResponseSchema,
  type DashboardSummary,
  type RecordsResponse,
} from '../types'

const SNAPSHOT_KEY = 'mbfd-eoc:last-rendered-dashboard:v2'

function markDashboardStale(parsed: DashboardSummary): DashboardSummary {
  const reason = `Showing cached information from ${parsed.metadata.generated_at}`
  return {
    ...parsed,
    metadata: {
      ...parsed.metadata,
      stale: true,
      source_health: 'stale',
      empty_state: reason,
    },
    records: parsed.records.map((record) => ({
      ...record,
      stale: true,
      stale_reason: reason,
    })),
  }
}

export async function fetchDashboard(signal?: AbortSignal): Promise<DashboardSummary> {
  try {
    const response = await fetch('/api/v1/dashboard/summary', {
      headers: {Accept: 'application/json'},
      signal,
      credentials: 'same-origin',
    })
    if (!response.ok) throw new Error(`Dashboard API returned ${response.status}`)
    const parsed = dashboardSummarySchema.parse(await response.json())
    if (response.headers.get('X-EOC-Cache')?.toLowerCase() === 'hit') {
      return markDashboardStale(parsed)
    }
    try {
      localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(parsed))
    } catch {
      // The service worker remains the second last-known-good layer.
    }
    return parsed
  } catch (error) {
    let snapshot: string | null = null
    try {
      snapshot = localStorage.getItem(SNAPSHOT_KEY)
    } catch {
      // Storage can be unavailable in private or quota-constrained browser contexts.
    }
    if (snapshot) {
      const parsed = dashboardSummarySchema.parse(JSON.parse(snapshot))
      return markDashboardStale(parsed)
    }
    throw error
  }
}

export async function fetchRadarStatus(signal?: AbortSignal): Promise<RecordsResponse> {
  const response = await fetch('/api/v1/radar/status', {
    headers: {Accept: 'application/json'},
    signal,
    credentials: 'same-origin',
  })
  if (!response.ok) throw new Error(`Radar status API returned ${response.status}`)
  return recordsResponseSchema.parse(await response.json())
}
