import type { Meta, StoryObj } from '@storybook/react'
import type { CatalogWork, Hold } from '../types'
import { fakePatron, fakeSession, withApi } from '../stories/helpers'
import { Browse } from './Browse'

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
    title: 'The Wapshot Chronicle',
    author: 'John Cheever',
    manifestations: [
      {
        id: 21,
        title: 'The Wapshot Chronicle',
        material_type: 'book',
        isbn: '9780000000002',
        publisher: 'Harper',
        items: [{ barcode: 'B010', availability: 'on_loan' }],
      },
      {
        id: 22,
        title: 'The Wapshot Chronicle (audiobook)',
        material_type: 'audiovisual',
        isbn: null,
        publisher: 'Audio Press',
        items: [{ barcode: 'A010', availability: 'available' }],
      },
    ],
  },
]

const hold: Hold = {
  hold_id: 9,
  manifestation_id: 11,
  patron_card: 'C001',
  queue_position: 2,
  status: 'pending',
}

// The public catalogue. `withApi` answers the same-origin paths the screen
// fetches, so these stories render real populated/empty states with no backend.
const meta: Meta<typeof Browse> = {
  title: 'OPAC/Browse',
  component: Browse,
  parameters: { layout: 'fullscreen' },
  args: { onNeedSignIn: () => {} },
}
export default meta

type Story = StoryObj<typeof Browse>

export const SignedOut: Story = {
  args: { session: fakeSession() },
  decorators: [withApi((path) => (path === '/catalog' ? CATALOG : undefined))],
}

export const SignedIn: Story = {
  args: { session: fakeSession({ patron: fakePatron() }) },
  decorators: [
    withApi((path, method) => {
      if (path === '/catalog') return CATALOG
      if (path === '/holds' && method === 'POST') return hold
      return undefined
    }),
  ],
}

export const EmptyCatalogue: Story = {
  args: { session: fakeSession() },
  decorators: [withApi((path) => (path === '/catalog' ? [] : undefined))],
}
