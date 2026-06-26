import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { runApi, type Result } from '../notify'
import type { LoanLine, PatronHold } from '../types'
import type { CardSession } from './useCardSession'

/** The patron's account: current loans and holds, with hold cancellation. */
export function MyLibrary({
  session,
  onSignIn,
}: {
  session: CardSession
  onSignIn: () => void
}) {
  const [loans, setLoans] = useState<LoanLine[]>([])
  const [holds, setHolds] = useState<PatronHold[]>([])
  const [msg, setMsg] = useState<Result | null>(null)
  const card = session.patron?.card_number

  const refresh = useCallback(() => {
    if (!card) return
    api.patronLoans(card).then(setLoans).catch(() => setLoans([]))
    api.patronHolds(card).then(setHolds).catch(() => setHolds([]))
  }, [card])

  useEffect(() => {
    refresh()
  }, [refresh])

  if (!session.patron) {
    return (
      <div className="opac-page">
        <div className="opac-empty" data-testid="opac-me-signedout">
          <p>Sign in with your library card to see your loans and holds.</p>
          <button className="btn" onClick={onSignIn}>
            Sign in
          </button>
        </div>
      </div>
    )
  }

  const cancel = async (holdId: number, title: string) => {
    const res = await runApi(async () => {
      await api.cancelHold(holdId)
      return `Hold on “${title}” cancelled.`
    })
    setMsg(res)
    if (res.ok) refresh()
  }

  return (
    <div className="opac-page">
      <div className="opac-hero compact">
        <h1 className="serif">My library</h1>
        <p className="muted">
          {session.patron.card_number} · {session.patron.category}
        </p>
        {msg && (
          <span
            className={msg.ok ? 'opac-flash ok' : 'opac-flash err'}
            data-testid="opac-me-flash"
          >
            {msg.text}
          </span>
        )}
      </div>

      <section className="opac-section">
        <h2 className="serif opac-section-title">On loan</h2>
        {loans.length === 0 ? (
          <div className="opac-empty small" data-testid="opac-loans-empty">
            Nothing on loan right now.
          </div>
        ) : (
          <ul className="opac-list" data-testid="opac-loans">
            {loans.map((l) => (
              <li className="opac-row" key={l.item_barcode} data-testid={`opac-loan-${l.item_barcode}`}>
                <div>
                  <div className="cell-title">{l.title}</div>
                  <div className="cell-sub">{l.author}</div>
                </div>
                <div className="opac-row-end">
                  <span className="muted">
                    due <span className="mono">{l.due_date}</span>
                  </span>
                  {l.overdue && (
                    <span className="pill lost">
                      <span className="dot" />
                      overdue
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="opac-section">
        <h2 className="serif opac-section-title">Holds</h2>
        {holds.length === 0 ? (
          <div className="opac-empty small" data-testid="opac-holds-empty">
            You have no holds.
          </div>
        ) : (
          <ul className="opac-list" data-testid="opac-holds">
            {holds.map((h) => (
              <li className="opac-row" key={h.hold_id} data-testid={`opac-myhold-${h.hold_id}`}>
                <div>
                  <div className="cell-title">{h.title}</div>
                  <div className="cell-sub">
                    {h.status === 'ready'
                      ? h.pickup_by
                        ? `ready — pick up by ${h.pickup_by}`
                        : 'ready for pickup'
                      : `#${h.queue_position} in the queue`}
                  </div>
                </div>
                <div className="opac-row-end">
                  <span className={`pill ${h.status === 'ready' ? 'on_hold_shelf' : ''}`}>
                    <span className="dot" />
                    {h.status === 'ready' ? 'ready' : 'waiting'}
                  </span>
                  <button
                    className="btn btn-secondary btn-sm"
                    data-testid={`opac-hold-cancel-${h.hold_id}`}
                    onClick={() => cancel(h.hold_id, h.title)}
                  >
                    Cancel
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
