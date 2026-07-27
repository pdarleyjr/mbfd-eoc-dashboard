import type {SourceHealthState} from '../types'

export function sourceStateLabel(state: SourceHealthState): string {
  const labels: Record<SourceHealthState, string> = {
    healthy: 'Healthy',
    delayed: 'Delayed',
    stale: 'Stale',
    unavailable: 'Unavailable',
    invalid_response: 'Invalid response',
    scraper_layout_changed: 'Scraper layout changed',
  }
  return labels[state]
}

export function causewayStatus(
  status: 'closure' | 'restriction' | 'no_closure' | undefined,
): string {
  if (status === 'closure') return 'Verified closure reported'
  if (status === 'restriction') return 'Restriction reported'
  if (status === 'no_closure') return 'No verified closure reported'
  return 'Source unavailable'
}

export function formatAge(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) return 'Age unavailable'
  if (seconds < 60) return `${Math.max(0, Math.floor(seconds))} seconds old`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} old`
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return `${hours} ${hours === 1 ? 'hour' : 'hours'}${remainder ? ` ${remainder} ${remainder === 1 ? 'minute' : 'minutes'}` : ''} old`
}

export function localTime(value: string | null | undefined): string {
  if (!value) return 'Not available'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return 'Not available'
  return new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(parsed)
}

export function recordTime(record: {
  observed_at: string | null
  published_at: string | null
  retrieved_at: string
}): string {
  return localTime(record.observed_at ?? record.published_at ?? record.retrieved_at)
}

export function valueText(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'Not available'
  if (typeof value === 'number') return new Intl.NumberFormat('en-US').format(value)
  if (typeof value === 'string' || typeof value === 'boolean' || typeof value === 'bigint')
    return String(value)
  return 'Not available'
}
