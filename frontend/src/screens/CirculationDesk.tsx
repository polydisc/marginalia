import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type { Notify } from '../notify'
import type {
  LoanLine,
  Patron,
  PatronCategory,
  PatronHold,
  ReadyHold,
} from '../types'
import { ActivityLog, type LogEntry } from '../components/ActivityLog'
import { IconBarcode, IconPlus } from '../icons'

type Mode = 'out' | 'in' | 'renew'

const MODES: { id: Mode; label: string }[] = [
  { id: 'out', label: 'Check out' },
  { id: 'in', label: 'Return' },
  { id: 'renew', label: 'Renew' },
]
const CATEGORIES: PatronCategory[] = ['general', 'student', 'child']
const today = new Date().toLocaleDateString('en-GB', {
  weekday: 'long',
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

export function CirculationDesk({
  notify,
  log,
}: {
  notify: Notify
  log: LogEntry[]
}) {
  const [mode, setMode] = useState<Mode>('out')
  const [card, setCard] = useState('C001')
  const [barcode, setBarcode] = useState('')
  const [session, setSession] = useState<Patron | null>(null)
  const [loans, setLoans] = useState<LoanLine[]>([])
  const [patronHolds, setPatronHolds] = useState<PatronHold[]>([])
  const [holds, setHolds] = useState<ReadyHold[]>([])

  // Register form
  const [regCard, setRegCard] = useState('')
  const [regCategory, setRegCategory] = useState<PatronCategory>('general')

  // Patron edit
  const [editPatron, setEditPatron] = useState(false)
  const [ePatCategory, setEPatCategory] = useState<PatronCategory>('general')
  const [ePatExpiry, setEPatExpiry] = useState('')

  const refreshHolds = useCallback(() => {
    api.readyHolds().then(setHolds).catch(() => setHolds([]))
  }, [])

  useEffect(() => {
    refreshHolds()
  }, [refreshHolds])

  // Close the patron edit panel whenever the loaded patron changes, so its
  // buffers can't be saved against a different patron.
  useEffect(() => {
    setEditPatron(false)
  }, [session?.card_number])

  const loadPatron = useCallback(async (c: string) => {
    const cc = c.trim().toUpperCase() // match how cards are stored on register
    if (!cc) return
    try {
      // The patron must resolve to load a session; loans/holds are secondary —
      // a hiccup in either shouldn't blank the whole patron.
      const patron = await api.getPatron(cc)
      setSession(patron)
      const [lines, ph] = await Promise.all([
        api.patronLoans(cc).catch(() => []),
        api.patronHolds(cc).catch(() => []),
      ])
      setLoans(lines)
      setPatronHolds(ph)
    } catch {
      setSession(null)
      setLoans([])
      setPatronHolds([])
    }
  }, [])

  const refreshSession = useCallback(() => {
    if (session) loadPatron(session.card_number)
  }, [session, loadPatron])

  const onScan = async (e: React.FormEvent) => {
    e.preventDefault()
    const bc = barcode.trim().toUpperCase()
    const cc = card.trim().toUpperCase()
    if (!bc) return
    let res
    if (mode === 'out') {
      res = await notify(async () => {
        const loan = await api.checkOut(bc, cc)
        return `Checked out ${loan.item_barcode} to ${loan.patron_card} — due ${loan.due_date}`
      })
      if (res.ok) await loadPatron(cc)
    } else if (mode === 'in') {
      res = await notify(async () => {
        const r = await api.checkIn(bc)
        return r.hold_triggered
          ? `Returned ${r.item_barcode} → set aside for hold #${r.ready_hold_id}`
          : `Returned ${r.item_barcode} — back on shelf`
      })
      if (res.ok) {
        refreshSession()
        refreshHolds()
      }
    } else {
      res = await notify(async () => {
        const loan = await api.renew(bc)
        return `Renewed ${loan.item_barcode} — now due ${loan.due_date} (renewals: ${loan.renewal_count})`
      })
      if (res.ok) refreshSession()
    }
    setBarcode('')
  }

  const returnItem = async (bc: string) => {
    const res = await notify(async () => {
      const r = await api.checkIn(bc)
      return r.hold_triggered
        ? `Returned ${r.item_barcode} → set aside for hold #${r.ready_hold_id}`
        : `Returned ${r.item_barcode} — back on shelf`
    })
    if (res.ok) {
      refreshSession()
      refreshHolds()
    }
  }

  const renewItem = async (bc: string) => {
    const res = await notify(async () => {
      const loan = await api.renew(bc)
      return `Renewed ${loan.item_barcode} — now due ${loan.due_date} (renewals: ${loan.renewal_count})`
    })
    if (res.ok) refreshSession()
  }

  const fulfilHold = async (h: ReadyHold) => {
    if (!h.item_barcode) return
    const res = await notify(async () => {
      const loan = await api.checkOut(h.item_barcode!, h.patron_card)
      return `Fulfilled hold #${h.hold_id}: ${h.title} checked out to ${loan.patron_card}`
    })
    if (res.ok) {
      refreshHolds()
      if (session?.card_number === h.patron_card) refreshSession()
    }
  }

  const cancelPatronHold = async (holdId: number) => {
    const res = await notify(async () => {
      const r = await api.cancelHold(holdId)
      return `Cancelled hold #${r.hold_id}${r.reassigned ? ' — reassigned to next in queue' : ''}`
    })
    if (res.ok) {
      refreshSession()
      refreshHolds()
    }
  }

  const runExpiry = async () => {
    const res = await notify(async () => {
      const r = await api.expireHolds()
      return `Expiry sweep — ${r.expired} expired, ${r.reassigned} reassigned`
    })
    if (res.ok) {
      refreshHolds()
      refreshSession()
    }
  }

  const setStatus = async (suspend: boolean) => {
    if (!session) return
    const res = await notify(async () => {
      const p = suspend
        ? await api.suspendPatron(session.card_number)
        : await api.reinstatePatron(session.card_number)
      return `${session.card_number} is now ${p.status}`
    })
    if (res.ok) refreshSession()
  }

  const startEditPatron = () => {
    if (!session) return
    setEPatCategory(session.category as PatronCategory)
    setEPatExpiry(session.expires_on ?? '')
    setEditPatron(true)
  }

  const savePatron = async () => {
    if (!session) return
    const res = await notify(async () => {
      const p = await api.updatePatron(
        session.card_number,
        ePatCategory,
        ePatExpiry || undefined,
      )
      return `Updated ${p.card_number} → ${p.category}${p.expires_on ? ` · expires ${p.expires_on}` : ''}`
    })
    if (res.ok) {
      setEditPatron(false)
      refreshSession()
    }
  }

  const register = async (e: React.FormEvent) => {
    e.preventDefault()
    const cc = regCard.trim().toUpperCase()
    if (!cc) return
    const res = await notify(async () => {
      const p = await api.registerPatron(cc, regCategory)
      return `Registered patron ${p.card_number} (${p.category})`
    })
    if (res.ok) {
      setRegCard('')
      setCard(cc)
      loadPatron(cc)
    }
  }

  const overdue = loans.filter((l) => l.overdue).length

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Circulation Desk</h1>
          <div className="sub mono">{today}</div>
        </div>
        <div className="spacer" />
        {overdue > 0 && (
          <span className="pill on_loan">
            <span className="dot" />
            {overdue} overdue
          </span>
        )}
      </header>

      <div className="page">
        <div className="stat-row">
          <div className="card stat">
            <span className="k">Holds ready</span>
            <span className="v tnum" data-testid="kpi-holds">
              {holds.length}
            </span>
            <span className="meta">on the hold shelf</span>
          </div>
          <div className="card stat">
            <span className="k">On loan · this patron</span>
            <span className="v tnum">{session ? loans.length : '—'}</span>
            <span className="meta">{session ? session.card_number : 'no patron loaded'}</span>
          </div>
          <div className="card stat">
            <span className="k">Overdue · this patron</span>
            <span className="v tnum">{session ? overdue : '—'}</span>
            <span className="meta">
              {session && overdue === 0 ? 'in good standing' : ' '}
            </span>
          </div>
        </div>

        <div className="desk">
          {/* PRIMARY */}
          <section className="flow">
            <div className="card card-pad flow">
              <div className="row between">
                <div className="eyebrow">Scan station</div>
                <div className="seg" role="tablist">
                  {MODES.map((m) => (
                    <button
                      key={m.id}
                      role="tab"
                      aria-selected={mode === m.id}
                      data-testid={`mode-${m.id}`}
                      onClick={() => setMode(m.id)}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="row" style={{ gap: 'var(--s4)', alignItems: 'stretch' }}>
                <label className="field" style={{ flex: 1, margin: 0 }}>
                  <span className="lbl">Patron card</span>
                  <input
                    className="input mono"
                    data-testid="desk-card"
                    value={card}
                    placeholder="C001"
                    onChange={(e) => setCard(e.target.value)}
                    onBlur={(e) => loadPatron(e.target.value)}
                  />
                </label>
                <label className="field" style={{ flex: 1.4, margin: 0 }}>
                  <span className="lbl">
                    Item barcode — {MODES.find((m) => m.id === mode)!.label.toLowerCase()}, then Enter
                  </span>
                  <form className="scan" style={{ marginTop: 0 }} onSubmit={onScan}>
                    <IconBarcode />
                    <input
                      data-testid="desk-barcode"
                      value={barcode}
                      placeholder="B001"
                      autoComplete="off"
                      onChange={(e) => setBarcode(e.target.value)}
                    />
                    <button className="btn btn-sm" type="submit" data-testid="desk-go">
                      Enter
                    </button>
                  </form>
                </label>
              </div>
            </div>

            <div className={`session${session ? '' : ' empty'}`}>
              <div className="face">{session ? session.card_number.slice(-2) : '—'}</div>
              <div style={{ flex: 1 }}>
                <div className="who" data-testid="session-who">
                  {session ? session.card_number : 'No patron in session'}
                </div>
                <div className="muted" style={{ fontSize: 'var(--step--1)' }} data-testid="session-meta">
                  {session
                    ? `${loans.length} on loan${overdue ? ` · ${overdue} overdue` : ''}`
                    : 'Enter a patron card to load their loans'}
                </div>
              </div>
              {session && (
                <>
                  <span className={`pill${session.status === 'suspended' ? ' lost' : ''}`}>
                    {session.status === 'suspended' ? session.status : session.category}
                  </span>
                  <button
                    className="btn btn-ghost btn-sm"
                    data-testid="session-edit"
                    onClick={() => (editPatron ? setEditPatron(false) : startEditPatron())}
                  >
                    {editPatron ? 'Close' : 'Edit'}
                  </button>
                  {session.status === 'suspended' ? (
                    <button
                      className="btn btn-secondary btn-sm"
                      data-testid="session-reinstate"
                      onClick={() => setStatus(false)}
                    >
                      Reinstate
                    </button>
                  ) : (
                    <button
                      className="btn btn-ghost btn-sm"
                      data-testid="session-suspend"
                      onClick={() => setStatus(true)}
                    >
                      Suspend
                    </button>
                  )}
                </>
              )}
            </div>

            {session && editPatron && (
              <div className="card card-pad row wrap" style={{ gap: 'var(--s3)', alignItems: 'end' }}>
                <label className="field" style={{ margin: 0 }}>
                  <span className="lbl">Category</span>
                  <select
                    className="select"
                    data-testid="patron-edit-category"
                    value={ePatCategory}
                    onChange={(e) => setEPatCategory(e.target.value as PatronCategory)}
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field" style={{ margin: 0 }}>
                  <span className="lbl">Card expiry</span>
                  <input
                    className="input"
                    type="date"
                    data-testid="patron-edit-expiry"
                    value={ePatExpiry}
                    onChange={(e) => setEPatExpiry(e.target.value)}
                  />
                </label>
                <button className="btn btn-sm" data-testid="patron-edit-save" onClick={savePatron}>
                  Save patron
                </button>
              </div>
            )}

            <div className="card">
              <div className="card-head">
                <h2>On loan</h2>
                <span className="muted" style={{ fontSize: 'var(--step--1)' }}>
                  {session ? `${loans.length} item${loans.length === 1 ? '' : 's'}` : '—'}
                </span>
              </div>
              <div style={{ overflow: 'auto' }}>
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>Barcode</th>
                      <th>Due</th>
                      <th>Renewals</th>
                      <th>State</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody data-testid="loan-body">
                    {!session ? (
                      <tr>
                        <td colSpan={6} className="muted" style={{ textAlign: 'center', padding: 34 }}>
                          Load a patron to see their loans.
                        </td>
                      </tr>
                    ) : loans.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="muted" style={{ textAlign: 'center', padding: 34 }}>
                          Nothing on loan for this patron.
                        </td>
                      </tr>
                    ) : (
                      loans.map((l) => (
                        <tr key={l.item_barcode} data-testid={`loan-${l.item_barcode}`}>
                          <td>
                            <div className="cell-title">{l.title}</div>
                            <div className="cell-sub">{l.author}</div>
                          </td>
                          <td className="num">{l.item_barcode}</td>
                          <td>
                            <span className="num">{l.due_date}</span>
                            {l.overdue && (
                              <span className="pill lost" style={{ padding: '1px 7px', marginLeft: 6 }}>
                                overdue
                              </span>
                            )}
                          </td>
                          <td className="num" style={{ textAlign: 'center' }}>
                            {l.renewal_count}
                          </td>
                          <td>
                            <span className="pill on_loan">
                              <span className="dot" />
                              on loan
                            </span>
                          </td>
                          <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                            <button
                              className="btn btn-ghost btn-sm"
                              onClick={() => renewItem(l.item_barcode)}
                            >
                              Renew
                            </button>{' '}
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => returnItem(l.item_barcode)}
                            >
                              Return
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {session && patronHolds.length > 0 && (
              <div className="card">
                <div className="card-head">
                  <h3>Holds</h3>
                  <span className="muted" style={{ fontSize: 'var(--step--1)' }}>
                    {patronHolds.length} active
                  </span>
                </div>
                <div data-testid="patron-holds">
                  {patronHolds.map((h) => (
                    <div className="hold-card" key={h.hold_id}>
                      <span className={`pill ${h.status === 'ready' ? 'on_hold_shelf' : ''}`}>
                        <span className="dot" />
                        {h.status === 'ready' ? 'ready' : `#${h.queue_position} in queue`}
                      </span>
                      <div style={{ flex: 1 }}>
                        <div className="cell-title">{h.title}</div>
                        <div className="cell-sub">
                          hold #{h.hold_id}
                          {h.pickup_by ? ` · pick up by ${h.pickup_by}` : ''}
                        </div>
                      </div>
                      <button
                        className="btn btn-secondary btn-sm"
                        data-testid={`hold-cancel-${h.hold_id}`}
                        onClick={() => cancelPatronHold(h.hold_id)}
                      >
                        Cancel
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* SIDE */}
          <section className="flow">
            <div className="card">
              <div className="card-head">
                <h3>Hold shelf</h3>
                <div className="spacer" />
                <button
                  className="btn btn-ghost btn-sm"
                  data-testid="expire-sweep"
                  onClick={runExpiry}
                  title="Expire ready holds past their pickup-by date"
                >
                  Run expiry
                </button>
                <span className="pill on_hold_shelf">
                  <span className="dot" />
                  ready
                </span>
              </div>
              <div data-testid="hold-shelf">
                {holds.length === 0 ? (
                  <div className="card-pad muted">No holds waiting on the shelf.</div>
                ) : (
                  holds.map((h) => (
                    <div className="hold-card" key={h.hold_id}>
                      <div className="q">{h.queue_position}</div>
                      <div style={{ flex: 1 }}>
                        <div className="cell-title">{h.title}</div>
                        <div className="cell-sub">
                          for {h.patron_card} · {h.item_barcode} · hold #{h.hold_id}
                        </div>
                      </div>
                      <button
                        className="btn btn-sm"
                        data-testid={`hold-fulfil-${h.hold_id}`}
                        disabled={!h.item_barcode}
                        onClick={() => fulfilHold(h)}
                      >
                        Check out
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="card">
              <div className="card-head">
                <h3>Register patron</h3>
              </div>
              <form className="card-pad flow" onSubmit={register}>
                <label className="field" style={{ margin: 0 }}>
                  <span className="lbl">Card number</span>
                  <input
                    className="input mono"
                    data-testid="reg-card"
                    value={regCard}
                    placeholder="C014"
                    onChange={(e) => setRegCard(e.target.value)}
                  />
                </label>
                <label className="field" style={{ margin: 0 }}>
                  <span className="lbl">Category</span>
                  <select
                    className="select"
                    data-testid="reg-category"
                    value={regCategory}
                    onChange={(e) => setRegCategory(e.target.value as PatronCategory)}
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </label>
                <button className="btn" type="submit" data-testid="reg-submit" style={{ width: '100%' }}>
                  <IconPlus />
                  Register patron
                </button>
              </form>
            </div>

            <div className="card">
              <div className="card-head">
                <h3>Activity</h3>
                <div className="spacer" />
                <span className="muted mono" style={{ fontSize: 11 }}>
                  live
                </span>
              </div>
              <ActivityLog entries={log} />
            </div>
          </section>
        </div>
      </div>
    </>
  )
}
