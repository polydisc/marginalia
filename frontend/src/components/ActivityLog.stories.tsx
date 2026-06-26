import type { Meta, StoryObj } from '@storybook/react'
import { ActivityLog } from './ActivityLog'

const meta: Meta<typeof ActivityLog> = {
  title: 'Components/ActivityLog',
  component: ActivityLog,
}
export default meta

type Story = StoryObj<typeof ActivityLog>

const at = (h: number, m: number) => new Date(2026, 5, 26, h, m)

export const Empty: Story = {
  args: { entries: [] },
}

export const WithActivity: Story = {
  args: {
    entries: [
      {
        id: 4,
        kind: 'err',
        text: '409 ItemNotAvailable: item B001 is already on loan',
        at: at(13, 26),
      },
      {
        id: 3,
        kind: 'ok',
        text: 'Returned B033 → set aside for hold #5',
        at: at(13, 24),
      },
      {
        id: 2,
        kind: 'ok',
        text: 'Checked out B001 to C001 — due 2026-07-10',
        at: at(13, 20),
      },
      {
        id: 1,
        kind: 'ok',
        text: 'Registered patron C001 (general)',
        at: at(13, 17),
      },
    ],
  },
}
