import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from '../api'
import type { Patron } from '../types'
import { useCardSession } from './useCardSession'

const patron = (card: string): Patron => ({
  id: 1,
  card_number: card,
  category: 'general',
  status: 'active',
  expires_on: null,
})

beforeEach(() => {
  localStorage.clear()
})
afterEach(() => {
  vi.restoreAllMocks()
})

describe('useCardSession', () => {
  it('starts signed out when nothing is persisted', () => {
    const getPatron = vi.spyOn(api, 'getPatron')
    const { result } = renderHook(() => useCardSession())

    expect(result.current.patron).toBeNull()
    expect(getPatron).not.toHaveBeenCalled()
  })

  it('restores and validates a persisted card on mount', async () => {
    localStorage.setItem('opac.card', 'C001')
    vi.spyOn(api, 'getPatron').mockResolvedValue(patron('C001'))

    const { result } = renderHook(() => useCardSession())

    await waitFor(() => expect(result.current.patron?.card_number).toBe('C001'))
    expect(api.getPatron).toHaveBeenCalledWith('C001')
  })

  it('drops a persisted card the backend no longer recognises', async () => {
    localStorage.setItem('opac.card', 'GONE')
    vi.spyOn(api, 'getPatron').mockRejectedValue(new ApiError(404, 'not found', 'NotFound'))

    const { result } = renderHook(() => useCardSession())

    await waitFor(() => expect(localStorage.getItem('opac.card')).toBeNull())
    expect(result.current.patron).toBeNull()
  })

  it('signIn trims, upper-cases, validates and persists the card', async () => {
    const getPatron = vi.spyOn(api, 'getPatron').mockResolvedValue(patron('C001'))
    const { result } = renderHook(() => useCardSession())

    await act(async () => {
      await result.current.signIn('  c001  ')
    })

    expect(getPatron).toHaveBeenCalledWith('C001')
    expect(result.current.patron?.card_number).toBe('C001')
    expect(localStorage.getItem('opac.card')).toBe('C001')
  })

  it('signIn propagates an ApiError and leaves the session signed out', async () => {
    vi.spyOn(api, 'getPatron').mockRejectedValue(new ApiError(404, 'not found', 'NotFound'))
    const { result } = renderHook(() => useCardSession())

    await expect(
      act(async () => {
        await result.current.signIn('NOPE')
      }),
    ).rejects.toBeInstanceOf(ApiError)
    expect(result.current.patron).toBeNull()
    expect(localStorage.getItem('opac.card')).toBeNull()
  })

  it('signOut clears the patron and the persisted card', async () => {
    vi.spyOn(api, 'getPatron').mockResolvedValue(patron('C001'))
    const { result } = renderHook(() => useCardSession())
    await act(async () => {
      await result.current.signIn('C001')
    })

    act(() => result.current.signOut())

    expect(result.current.patron).toBeNull()
    expect(localStorage.getItem('opac.card')).toBeNull()
  })
})
