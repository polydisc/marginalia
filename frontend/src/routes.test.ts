import { afterEach, describe, expect, it } from 'vitest'
import { navigate, parseRoute } from './routes'

describe('parseRoute', () => {
  it('defaults to the staff circulation desk', () => {
    expect(parseRoute('')).toEqual({ shell: 'staff', screen: 'desk' })
    expect(parseRoute('#')).toEqual({ shell: 'staff', screen: 'desk' })
  })

  it('routes the bare #catalog hash to the staff catalog', () => {
    expect(parseRoute('#catalog')).toEqual({ shell: 'staff', screen: 'catalog' })
  })

  it('treats #/opac and its descendants as the patron browse screen', () => {
    expect(parseRoute('#/opac')).toEqual({ shell: 'opac', screen: 'browse' })
    expect(parseRoute('#/opac/')).toEqual({ shell: 'opac', screen: 'browse' })
    expect(parseRoute('#/opac/anything')).toEqual({ shell: 'opac', screen: 'browse' })
  })

  it('routes #/opac/me to the patron "my library" screen', () => {
    expect(parseRoute('#/opac/me')).toEqual({ shell: 'opac', screen: 'me' })
  })

  it('tolerates a hash with no leading "#"', () => {
    expect(parseRoute('/opac/me')).toEqual({ shell: 'opac', screen: 'me' })
    expect(parseRoute('catalog')).toEqual({ shell: 'staff', screen: 'catalog' })
  })

  it('falls back to the desk for an unknown staff hash', () => {
    expect(parseRoute('#nonsense')).toEqual({ shell: 'staff', screen: 'desk' })
  })
})

describe('navigate', () => {
  afterEach(() => {
    window.location.hash = ''
  })

  it('writes the hash onto window.location', () => {
    navigate('/opac/me')
    expect(window.location.hash).toBe('#/opac/me')
  })
})
