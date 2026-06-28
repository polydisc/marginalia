import type { Meta, StoryObj } from '@storybook/react'
import { ApiError } from '../api'
import { fakeSession } from '../stories/helpers'
import { SignIn } from './SignIn'

// The card-number sign-in modal. The session is faked, so these stories never
// touch the backend; type a card and submit to drive the success/error paths.
const meta: Meta<typeof SignIn> = {
  title: 'OPAC/SignIn',
  component: SignIn,
  parameters: { layout: 'fullscreen' },
  args: { onClose: () => {} },
}
export default meta

type Story = StoryObj<typeof SignIn>

export const Default: Story = {
  args: {
    // A valid card resolves and the modal closes via onClose.
    session: fakeSession(),
  },
}

export const UnknownCard: Story = {
  name: 'Unknown card (404)',
  args: {
    session: fakeSession({
      signIn: async () => {
        throw new ApiError(404, 'not found', 'NotFound')
      },
    }),
  },
}

export const ServerError: Story = {
  args: {
    session: fakeSession({
      signIn: async () => {
        throw new ApiError(500, 'boom', 'Server')
      },
    }),
  },
}
