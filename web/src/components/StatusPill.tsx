import {
  CheckmarkCircle16Regular,
  ClockAlarm16Regular,
  ErrorCircle16Regular,
  Warning16Regular,
} from '@fluentui/react-icons'
import type {SourceHealthState} from '../types'
import {sourceStateLabel} from '../lib/format'

export function StatusPill({
  state,
  onClick,
  ariaLabel,
}: {
  state: SourceHealthState
  onClick?: () => void
  ariaLabel?: string
}) {
  const Icon =
    state === 'healthy'
      ? CheckmarkCircle16Regular
      : state === 'delayed' || state === 'stale'
        ? ClockAlarm16Regular
        : state === 'unavailable'
          ? ErrorCircle16Regular
          : Warning16Regular
  const contents = (
    <>
      <Icon aria-hidden />
      {sourceStateLabel(state)}
    </>
  )
  if (onClick)
    return (
      <button
        type="button"
        className={`status-pill status-${state} status-pill-button`}
        aria-label={ariaLabel}
        onClick={onClick}
      >
        {contents}
      </button>
    )
  return <span className={`status-pill status-${state}`}>{contents}</span>
}
