import type { Meta, StoryObj } from '@storybook/react'
import type { LoanLine, PatronHold } from '../types'
import { fakePatron, fakeSession, withApi } from '../stories/helpers'
import { MyLibrary } from './MyLibrary'

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
    title: 'The Recognitions',
    author: 'William Gaddis',
    due_date: '2026-06-01',
    renewal_count: 1,
    overdue: true,
  },
]

const HOLDS: PatronHold[] = [
  {
    hold_id: 5,
    manifestation_id: 11,
    title: 'Pale Fire',
    status: 'ready',
    queue_position: 0,
    pickup_by: '2026-07-02',
  },
  {
    hold_id: 6,
    manifestation_id: 21,
    title: 'Infinite Jest',
    status: 'pending',
    queue_position: 2,
    pickup_by: null,
  },
]

function account(loans: LoanLine[], holds: PatronHold[]) {
  return withApi((path) => {
    if (path.endsWith('/loans')) return loans
    if (path.endsWith('/holds')) return holds
    return undefined
  })
}

// The patron's account view: current loans and holds. The session is faked and
// `withApi` answers the loan/hold lookups for the active card.
const meta: Meta<typeof MyLibrary> = {
  title: 'OPAC/MyLibrary',
  component: MyLibrary,
  parameters: { layout: 'fullscreen' },
  args: { onSignIn: () => {} },
}
export default meta

type Story = StoryObj<typeof MyLibrary>

export const SignedOut: Story = {
  args: { session: fakeSession() },
}

export const WithLoansAndHolds: Story = {
  args: { session: fakeSession({ patron: fakePatron() }) },
  decorators: [account(LOANS, HOLDS)],
}

export const Empty: Story = {
  args: { session: fakeSession({ patron: fakePatron() }) },
  decorators: [account([], [])],
}
