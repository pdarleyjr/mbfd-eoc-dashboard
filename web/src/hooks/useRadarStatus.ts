import {useQuery} from '@tanstack/react-query'
import {fetchRadarStatus} from '../lib/api'

export function useRadarStatus(enabled: boolean) {
  return useQuery({
    queryKey: ['radar-status'],
    queryFn: ({signal}) => fetchRadarStatus(signal),
    enabled,
    refetchInterval: enabled ? 60_000 : false,
    staleTime: 45_000,
    retry: 2,
  })
}
