import {useQuery} from '@tanstack/react-query'
import {fetchDashboard} from '../lib/api'

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: ({signal}) => fetchDashboard(signal),
    refetchInterval: (query) => {
      const active = query.state.data?.records.some(
        (record) => record.category === 'pulsepoint_call' && record.payload.state === 'active',
      )
      const base = active ? 15_000 : 45_000
      return Math.round(base * (0.95 + Math.random() * 0.1))
    },
    staleTime: 10_000,
    retry: 2,
    retryDelay: (attempt) => Math.min(8000, 1000 * 2 ** attempt),
  })
}
