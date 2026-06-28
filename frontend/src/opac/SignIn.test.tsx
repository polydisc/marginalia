import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api'
import { SignIn } from './SignIn'
import type { CardSession } from './useCardSession'

function makeSession(over: Partial<CardSession> = {}): CardSession {
  return {
    patron: null,
    signIn: vi.fn(),
    signOut: vi.fn(),
    ...over,
  }
}

describe('SignIn', () => {
  it('signs in with the entered card and closes on success', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn().mockResolvedValue({})
    const onClose = vi.fn()
    render(<SignIn session={makeSession({ signIn })} onClose={onClose} />)

    await user.type(screen.getByTestId('opac-signin-card'), 'c001')
    await user.click(screen.getByTestId('opac-signin-submit'))

    expect(signIn).toHaveBeenCalledWith('c001')
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('shows a friendly not-found message for an unknown card (404)', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn().mockRejectedValue(new ApiError(404, 'not found', 'NotFound'))
    const onClose = vi.fn()
    render(<SignIn session={makeSession({ signIn })} onClose={onClose} />)

    await user.type(screen.getByTestId('opac-signin-card'), 'nope')
    await user.click(screen.getByTestId('opac-signin-submit'))

    expect(await screen.findByTestId('opac-signin-error')).toHaveTextContent(
      "We couldn't find card NOPE.",
    )
    expect(onClose).not.toHaveBeenCalled()
  })

  it('shows a generic message for a non-404 failure', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn().mockRejectedValue(new ApiError(500, 'boom', 'Server'))
    render(<SignIn session={makeSession({ signIn })} onClose={vi.fn()} />)

    await user.type(screen.getByTestId('opac-signin-card'), 'c001')
    await user.click(screen.getByTestId('opac-signin-submit'))

    expect(await screen.findByTestId('opac-signin-error')).toHaveTextContent(
      'Something went wrong — please try again.',
    )
  })

  it('does not call signIn when the card field is blank', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn()
    render(<SignIn session={makeSession({ signIn })} onClose={vi.fn()} />)

    await user.click(screen.getByTestId('opac-signin-submit'))
    expect(signIn).not.toHaveBeenCalled()
  })

  it('closes without signing in when Cancel is pressed', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn()
    const onClose = vi.fn()
    render(<SignIn session={makeSession({ signIn })} onClose={onClose} />)

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onClose).toHaveBeenCalledOnce()
    expect(signIn).not.toHaveBeenCalled()
  })
})
