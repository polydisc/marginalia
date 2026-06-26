import { useState } from 'react'
import { ApiError } from '../api'
import type { CardSession } from './useCardSession'

/** A lightweight card-number sign-in (no password) shown as a modal. */
export function SignIn({
  session,
  onClose,
}: {
  session: CardSession
  onClose: () => void
}) {
  const [card, setCard] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const cc = card.trim()
    if (!cc) return
    setBusy(true)
    setError('')
    try {
      await session.signIn(cc)
      onClose()
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? `We couldn't find card ${cc.toUpperCase()}.`
          : 'Something went wrong — please try again.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="opac-modal-scrim" onClick={onClose}>
      <div
        className="opac-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Sign in with your library card"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="serif">Sign in</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Enter your library card number to place holds and see your account.
        </p>
        <form className="flow" onSubmit={submit}>
          <label className="field" style={{ margin: 0 }}>
            <span className="lbl">Library card</span>
            <input
              className="input mono"
              data-testid="opac-signin-card"
              autoFocus
              value={card}
              placeholder="C001"
              onChange={(e) => setCard(e.target.value)}
            />
          </label>
          {error && (
            <div className="opac-error" data-testid="opac-signin-error">
              {error}
            </div>
          )}
          <div className="row" style={{ justifyContent: 'flex-end', gap: 'var(--s2)' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn"
              data-testid="opac-signin-submit"
              disabled={busy}
            >
              Sign in
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
