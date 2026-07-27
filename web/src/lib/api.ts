import {dashboardSummarySchema, type DashboardSummary} from '../types'

const SNAPSHOT_KEY = 'mbfd-eoc:last-rendered-dashboard:v1'

export async function fetchDashboard(signal?: AbortSignal): Promise<DashboardSummary> {
  try {
    const response = await fetch('/api/v1/dashboard/summary', {
      headers: {Accept: 'application/json'},
      signal,
      credentials: 'same-origin',
    })
    if (!response.ok) throw new Error(`Dashboard API returned ${response.status}`)
    const parsed = dashboardSummarySchema.parse(await response.json())
    try {
      localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(parsed))
    } catch {
      // The service worker remains the second last-known-good layer.
    }
    return parsed
  } catch (error) {
    const snapshot = localStorage.getItem(SNAPSHOT_KEY)
    if (snapshot) {
      const parsed = dashboardSummarySchema.parse(JSON.parse(snapshot))
      return {
        ...parsed,
        metadata: {
          ...parsed.metadata,
          stale: true,
          source_health: 'stale',
          empty_state: `Showing cached information from ${parsed.metadata.generated_at}`,
        },
        records: parsed.records.map((record) => ({
          ...record,
          stale: true,
          stale_reason: `Showing cached information from ${parsed.metadata.generated_at}`,
        })),
      }
    }
    throw error
  }
}
