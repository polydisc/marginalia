import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type { Patron } from '../types'

const KEY = 'opac.card'

export type CardSession = {
  patron: Patron | null
  /** Validate a card against the backend and persist it; throws ApiError on 404. */
  signIn: (card: string) => Promise<Patron>
  signOut: () => void
}

/**
 * The patron's identity in the OPAC: a card number only (no password). The card
 * is validated via `GET /patrons/{card}`, persisted in localStorage, and
 * restored on reload. There is no patron name in the domain, so callers greet by
 * card number + category.
 */
export function useCardSession(): CardSession {
  const [patron, setPatron] = useState<Patron | null>(null)

  useEffect(() => {
    const saved = localStorage.getItem(KEY)
    if (!saved) return
    api
      .getPatron(saved)
      .then(setPatron)
      .catch(() => localStorage.removeItem(KEY))
  }, [])

  const signIn = useCallback(async (card: string) => {
    const cc = card.trim().toUpperCase()
    const p = await api.getPatron(cc) // throws ApiError(404) on an unknown card
    localStorage.setItem(KEY, p.card_number)
    setPatron(p)
    return p
  }, [])

  const signOut = useCallback(() => {
    localStorage.removeItem(KEY)
    setPatron(null)
  }, [])

  return { patron, signIn, signOut }
}
