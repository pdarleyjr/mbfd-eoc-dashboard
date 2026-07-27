import {
  CheckmarkCircle16Regular,
  ClockAlarm16Regular,
  ErrorCircle16Regular,
  Warning16Regular,
} from '@fluentui/react-icons'
import type {SourceHealthState} from '../types'
import {sourceStateLabel} from '../lib/format'

export function StatusPill({state}: {state: SourceHealthState}) {
  const Icon =
    state === 'healthy'
      ? CheckmarkCircle16Regular
      : state === 'delayed' || state === 'stale'
        ? ClockAlarm16Regular
        : state === 'unavailable'
          ? ErrorCircle16Regular
          : Warning16Regular
  return (
    <span className={`status-pill status-${state}`}>
      <Icon aria-hidden />
      {sourceStateLabel(state)}
    </span>
  )
}
