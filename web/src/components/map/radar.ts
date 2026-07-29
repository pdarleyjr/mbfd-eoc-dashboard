export function windowedRadarFrames(frames: string[], minutes: number): string[] {
  const ordered = [...new Set(frames)]
    .filter((frame) => Number.isFinite(Date.parse(frame)))
    .sort((first, second) => Date.parse(first) - Date.parse(second))
  const latest = ordered.at(-1)
  if (!latest) return []
  const threshold = Date.parse(latest) - minutes * 60_000
  return ordered.filter((frame) => Date.parse(frame) >= threshold)
}

function frameClock(frame: string): string {
  return new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(new Date(frame))
}

export function radarStatusText(
  frame: string | undefined,
  now: Date,
  unavailable: boolean,
): string {
  if (!frame) return unavailable ? 'Radar unavailable · No verified frame' : 'Radar frame pending'
  if (unavailable) return `Radar unavailable · Last verified frame ${frameClock(frame)}`
  const ageMinutes = Math.max(0, Math.round((now.getTime() - Date.parse(frame)) / 60_000))
  if (ageMinutes > 10) return `Radar delayed · Last frame ${frameClock(frame)}`
  return `NOAA MRMS · Frame ${frameClock(frame)} · ${ageMinutes} ${
    ageMinutes === 1 ? 'minute' : 'minutes'
  } old`
}
