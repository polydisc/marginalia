import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import type { CatalogWork, Patron } from '../types'
import { Browse } from './Browse'
import type { CardSession } from './useCardSession'

const CATALOG: CatalogWork[] = [
  {
    id: 1,
    title: 'Dubliners',
    author: 'James Joyce',
    manifestations: [
      {
        id: 11,
        title: 'Dubliners',
        material_type: 'book',
        isbn: '9780000000001',
        publisher: 'Grant Richards',
        items: [
          { barcode: 'B001', availability: 'available' },
          { barcode: 'B002', availability: 'on_loan' },
        ],
      },
    ],
  },
  {
    id: 2,
    title: 'Jazz Standards',
    author: 'Various',
    manifestations: [
      {
        id: 21,
        title: 'Jazz Standards',
        material_type: 'audiovisual',
        isbn: null,
        publisher: null,
        items: [{ barcode: 'A001', availability: 'on_loan' }],
      },
    ],
  },
]

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

beforeEach(() => {
  vi.spyOn(api, 'getCatalog').mockResolvedValue(CATALOG)
})
afterEach(() => {
  vi.restoreAllMocks()
})

describe('Browse', () => {
  it('lists every catalogued work with its availability summary', async () => {
    render(<Browse session={session()} onNeedSignIn={vi.fn()} />)

    expect(await screen.findByTestId('opac-work-1')).toBeInTheDocument()
    expect(screen.getByTestId('opac-result-count')).toHaveTextContent('2 titles · 3 copies')
    expect(within(screen.getByTestId('opac-work-1')).getByText('1 of 2 available')).toBeInTheDocument()
    expect(within(screen.getByTestId('opac-work-2')).getByText('all copies out')).toBeInTheDocument()
  })

  it('filters the list by free-text query across title, author and ISBN', async () => {
    const user = userEvent.setup()
    render(<Browse session={session()} onNeedSignIn={vi.fn()} />)
    await screen.findByTestId('opac-work-1')

    await user.type(screen.getByTestId('opac-q'), 'joyce')

    expect(screen.getByTestId('opac-work-1')).toBeInTheDocument()
    expect(screen.queryByTestId('opac-work-2')).not.toBeInTheDocument()
    expect(screen.getByTestId('opac-result-count')).toHaveTextContent('1 title')
  })

  it('filters by material type and shows the empty state when nothing matches', async () => {
    const user = userEvent.setup()
    render(<Browse session={session()} onNeedSignIn={vi.fn()} />)
    await screen.findByTestId('opac-work-1')

    await user.click(screen.getByTestId('opac-filter-reference'))

    expect(screen.queryByTestId('opac-works')).not.toBeInTheDocument()
    expect(screen.getByTestId('opac-empty')).toBeInTheDocument()
  })

  it('prompts an anonymous patron to sign in instead of placing a hold', async () => {
    const user = userEvent.setup()
    const onNeedSignIn = vi.fn()
    const placeHold = vi.spyOn(api, 'placeHold')
    render(<Browse session={session()} onNeedSignIn={onNeedSignIn} />)
    await screen.findByTestId('opac-work-1')

    await user.click(screen.getByTestId('opac-hold-11'))

    expect(onNeedSignIn).toHaveBeenCalledOnce()
    expect(placeHold).not.toHaveBeenCalled()
  })

  it('places a hold for a signed-in patron and flashes the queue position', async () => {
    const user = userEvent.setup()
    vi.spyOn(api, 'placeHold').mockResolvedValue({
      hold_id: 9,
      manifestation_id: 11,
      patron_card: 'C001',
      queue_position: 3,
      status: 'pending',
    })
    render(<Browse session={session({ patron: patron('C001') })} onNeedSignIn={vi.fn()} />)
    await screen.findByTestId('opac-work-1')

    await user.click(screen.getByTestId('opac-hold-11'))

    expect(api.placeHold).toHaveBeenCalledWith(11, 'C001')
    await waitFor(() =>
      expect(screen.getByTestId('opac-flash')).toHaveTextContent("you're #3 in the queue"),
    )
  })
})
