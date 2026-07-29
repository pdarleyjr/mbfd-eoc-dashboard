import {describe, expect, it} from 'vitest'
import {pulsePointCallLabel} from './pulsepoint'

describe('PulsePoint call labels', () => {
  it('expands the medical emergency code for operational readability', () => {
    expect(pulsePointCallLabel('ME')).toBe('MED')
  })

  it('preserves other short source codes in uppercase', () => {
    expect(pulsePointCallLabel('fa')).toBe('FA')
  })

  it('rejects missing or unsafe marker content', () => {
    expect(pulsePointCallLabel('')).toBeNull()
    expect(pulsePointCallLabel('<img>')).toBeNull()
    expect(pulsePointCallLabel(null)).toBeNull()
  })
})
