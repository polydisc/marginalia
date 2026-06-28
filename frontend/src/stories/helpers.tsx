import type { Decorator } from '@storybook/react'
import { useEffect } from 'react'
import type { CardSession } from '../opac/useCardSession'
import type { Patron } from '../types'

/** A fake OPAC session for stories — no backend, no localStorage. */
export function fakeSession(over: Partial<CardSession> = {}): CardSession {
  return {
    patron: null,
    signIn: async (card) => fakePatron({ card_number: card.trim().toUpperCase() }),
    signOut: () => {},
    ...over,
  }
}

export function fakePatron(over: Partial<Patron> = {}): Patron {
  return {
    id: 1,
    card_number: 'C001',
    category: 'general',
    status: 'active',
    expires_on: null,
    ...over,
  }
}

/**
 * Returns whatever the handler returns for a given (path, method); `undefined`
 * is served as a 404. Components in the OPAC fetch same-origin relative paths,
 * so a story only needs to answer the handful its screen calls.
 */
type FetchHandler = (path: string, method: string) => unknown | undefined

interface StubFetch {
  (input: RequestInfo | URL, init?: RequestInit): Promise<Response>
  __storyOriginal?: typeof fetch
}

/** Decorator that answers the component's `fetch` calls from an in-memory handler. */
export function withApi(handler: FetchHandler): Decorator {
  return function ApiDecorator(Story) {
    // Don't capture a previously-installed story stub as the "original".
    const current = window.fetch as StubFetch
    const original = current.__storyOriginal ?? window.fetch

    const stub: StubFetch = async (input, init) => {
      const url = typeof input === 'string' ? input : input.toString()
      const path = url.replace(/^https?:\/\/[^/]+/, '')
      const method = (init?.method ?? 'GET').toUpperCase()
      const body = handler(path, method)
      return new Response(JSON.stringify(body ?? null), {
        status: body === undefined ? 404 : 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    stub.__storyOriginal = original
    window.fetch = stub as typeof fetch

    return (
      <RestoreFetch original={original}>
        <Story />
      </RestoreFetch>
    )
  }
}

function RestoreFetch({
  original,
  children,
}: {
  original: typeof fetch
  children: React.ReactNode
}) {
  useEffect(() => () => void (window.fetch = original), [original])
  return <>{children}</>
}
