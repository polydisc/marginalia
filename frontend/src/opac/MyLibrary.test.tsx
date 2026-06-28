import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import type { LoanLine, Patron, PatronHold } from '../types'
import { MyLibrary } from './MyLibrary'
import type { CardSession } from './useCardSession'

const patron = (card: string): Patron => ({
  id: 1,
  card_number: card,
  category: 'general',
  status: 'active',
  expires_on: null,
})

function session(over: Partial<CardSession> = {}): CardSession {
  return { patron: null, signIn: vi.fn(), signOut: vi.fn(), ...over }
}

const LOANS: LoanLine[] = [
  {
    item_barcode: 'B001',
    title: 'Dubliners',
    author: 'James Joyce',
    due_date: '2026-07-10',
    renewal_count: 0,
    overdue: false,
  },
  {
    item_barcode: 'B009',
    title: 'Overdue Tales',
    author: 'Anon',
    due_date: '2026-06-01',
    renewal_count: 1,
    overdue: true,
  },
]

const HOLDS: PatronHold[] = [
  {
    hold_id: 5,
    manifestation_id: 11,
    title: 'Ready Reader',
    status: 'ready',
    queue_position: 0,
    pickup_by: '2026-07-02',
  },
  {
    hold_id: 6,
    manifestation_id: 21,
    title: 'Waiting Work',
    status: 'pending',
    queue_position: 2,
    pickup_by: null,
  },
]

afterEach(() => {
  vi.restoreAllMocks()
})

describe('MyLibrary', () => {
  it('asks an anonymous visitor to sign in', () => {
    const onSignIn = vi.fn()
    render(<MyLibrary session={session()} onSignIn={onSignIn} />)

    expect(screen.getByTestId('opac-me-signedout')).toBeInTheDocument()
    expect(screen.queryByTestId('opac-loans')).not.toBeInTheDocument()
  })

  describe('signed in', () => {
    beforeEach(() => {
      vi.spyOn(api, 'patronLoans').mockResolvedValue(LOANS)
      vi.spyOn(api, 'patronHolds').mockResolvedValue(HOLDS)
    })

    it('loads the patron loans and holds for the active card', async () => {
      render(<MyLibrary session={session({ patron: patron('C001') })} onSignIn={vi.fn()} />)

      expect(await screen.findByTestId('opac-loans')).toBeInTheDocument()
      expect(api.patronLoans).toHaveBeenCalledWith('C001')
      expect(api.patronHolds).toHaveBeenCalledWith('C001')

      const overdue = screen.getByTestId('opac-loan-B009')
      expect(within(overdue).getByText('overdue')).toBeInTheDocument()

      const ready = screen.getByTestId('opac-myhold-5')
      expect(within(ready).getByText('ready — pick up by 2026-07-02')).toBeInTheDocument()
      const waiting = screen.getByTestId('opac-myhold-6')
      expect(within(waiting).getByText('#2 in the queue')).toBeInTheDocument()
    })

    it('cancels a hold and refreshes the lists on success', async () => {
      const user = userEvent.setup()
      vi.spyOn(api, 'cancelHold').mockResolvedValue({
        hold_id: 6,
        status: 'cancelled',
        reassigned: 0,
      })
      render(<MyLibrary session={session({ patron: patron('C001') })} onSignIn={vi.fn()} />)
      await screen.findByTestId('opac-holds')

      await user.click(screen.getByTestId('opac-hold-cancel-6'))

      expect(api.cancelHold).toHaveBeenCalledWith(6)
      await waitFor(() =>
        expect(screen.getByTestId('opac-me-flash')).toHaveTextContent(
          'Hold on “Waiting Work” cancelled.',
        ),
      )
      // A successful cancel triggers refresh(), re-querying the holds list
      // beyond the initial mount load. Count left loose (>= 2) so it doesn't
      // couple to how many lists refresh touches or to StrictMode re-runs.
      await waitFor(() =>
        expect(vi.mocked(api.patronHolds).mock.calls.length).toBeGreaterThanOrEqual(2),
      )
    })
  })

  it('shows empty-state copy when the patron has no loans or holds', async () => {
    vi.spyOn(api, 'patronLoans').mockResolvedValue([])
    vi.spyOn(api, 'patronHolds').mockResolvedValue([])
    render(<MyLibrary session={session({ patron: patron('C001') })} onSignIn={vi.fn()} />)

    expect(await screen.findByTestId('opac-loans-empty')).toBeInTheDocument()
    expect(screen.getByTestId('opac-holds-empty')).toBeInTheDocument()
  })
})
