import {describe, expect, it} from 'vitest'
import {causewayStatus, formatAge, sourceStateLabel} from './format'

describe('honest display formatting', () => {
  it('never turns an empty causeway response into open', () => {
    expect(causewayStatus(undefined)).toBe('Source unavailable')
  })

  it('uses the approved phrase for an explicit closure', () => {
    expect(causewayStatus('closure')).toBe('Verified closure reported')
  })

  it('labels scraper drift in plain language', () => {
    expect(sourceStateLabel('scraper_layout_changed')).toBe('Scraper layout changed')
  })

  it('formats data age without calling retrieval current', () => {
    expect(formatAge(3661)).toBe('1 hour 1 minute old')
  })
})
