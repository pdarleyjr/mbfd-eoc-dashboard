import {describe, expect, it} from 'vitest'
import {radarStatusText, windowedRadarFrames} from './radar'

describe('radar controls', () => {
  const frames = [
    '2026-07-29T11:40:00Z',
    '2026-07-29T12:00:00Z',
    '2026-07-29T12:20:00Z',
    '2026-07-29T12:40:00Z',
  ]

  it('uses only exact service-reported frames inside the selected window', () => {
    expect(windowedRadarFrames(frames, 60)).toEqual([
      '2026-07-29T11:40:00Z',
      '2026-07-29T12:00:00Z',
      '2026-07-29T12:20:00Z',
      '2026-07-29T12:40:00Z',
    ])
    expect(windowedRadarFrames(frames, 30)).toEqual([
      '2026-07-29T12:20:00Z',
      '2026-07-29T12:40:00Z',
    ])
  })

  it('never labels stale radar as live', () => {
    expect(
      radarStatusText('2026-07-29T12:40:00Z', new Date('2026-07-29T12:46:00Z'), false),
    ).toMatch(/NOAA MRMS.*6 minutes old/)
    const stale = radarStatusText('2026-07-29T12:40:00Z', new Date('2026-07-29T13:00:00Z'), false)
    expect(stale).toMatch(/^Radar delayed · Last frame/)
    expect(stale).not.toMatch(/live/i)
  })

  it('reports source unavailability without presenting a frame as current', () => {
    expect(radarStatusText('2026-07-29T12:40:00Z', new Date('2026-07-29T12:41:00Z'), true)).toBe(
      'Radar unavailable · Last verified frame 8:40 AM EDT',
    )
  })
})
