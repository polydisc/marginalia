import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import type { Notify } from '../notify'
import type { CatalogWork, MaterialType } from '../types'
import { IconChevron, IconPlus, IconSearch } from '../icons'

const FILTERS: ('all' | MaterialType)[] = ['all', 'book', 'reference', 'audiovisual']
const MATERIALS: MaterialType[] = ['book', 'reference', 'audiovisual']
const DOT: Record<string, string> = {
  available: 'da',
  on_loan: 'dl',
  on_hold_shelf: 'dh',
}

// Intrinsic-state actions offered per derived availability (mirrors the backend
// transition table). Items in use (on_loan / on_hold_shelf / withdrawn) offer none.
const STATE_ACTIONS: Record<string, { value: string; label: string }[]> = {
  available: [
    { value: 'in_repair', label: 'to repair' },
    { value: 'lost', label: 'mark lost' },
    { value: 'withdrawn', label: 'withdraw' },
  ],
  in_repair: [
    { value: 'available', label: 'shelve' },
    { value: 'lost', label: 'mark lost' },
    { value: 'withdrawn', label: 'withdraw' },
  ],
  lost: [
    { value: 'available', label: 'found — shelve' },
    { value: 'withdrawn', label: 'withdraw' },
  ],
}

export function Catalog({ notify }: { notify: Notify }) {
  const [works, setWorks] = useState<CatalogWork[]>([])
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<'all' | MaterialType>('all')
  const [open, setOpen] = useState<Set<number>>(new Set())
  const [holdCard, setHoldCard] = useState('C001')

  // Catalog-a-title form
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [material, setMaterial] = useState<MaterialType>('book')
  const [isbn, setIsbn] = useState('')
  const [barcode, setBarcode] = useState('')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const refresh = useCallback(() => {
    api.getCatalog().then(setWorks).catch(() => setWorks([]))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    return works.filter((w) => {
      const mats = w.manifestations.map((m) => m.material_type)
      if (filter !== 'all' && !mats.includes(filter)) return false
      if (!q) return true
      const hay = (
        w.title +
        ' ' +
        w.author +
        ' ' +
        w.manifestations.map((m) => m.isbn ?? '').join(' ')
      ).toLowerCase()
      return hay.includes(q)
    })
  }, [works, query, filter])

  const copies = (w: CatalogWork) =>
    w.manifestations.reduce((n, m) => n + m.items.length, 0)
  const avail = (w: CatalogWork) =>
    w.manifestations.reduce(
      (n, m) => n + m.items.filter((i) => i.availability === 'available').length,
      0,
    )

  const toggle = (id: number) =>
    setOpen((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  const submitCatalog = async (e: React.FormEvent) => {
    e.preventDefault()
    const t = title.trim()
    const a = author.trim()
    const bc = barcode.trim().toUpperCase()
    if (!t || !a || !bc) return
    const res = await notify(async () => {
      const work = await api.createWork(t, a)
      const man = await api.catalogManifestation(work.id, t, material, isbn.trim() || undefined)
      const item = await api.addItem(man.id, bc)
      setOpen((prev) => new Set(prev).add(work.id))
      return `Catalogued “${t}” → manifestation #${man.id}, item ${item.barcode} (${item.state})`
    })
    setMsg(res)
    if (res.ok) {
      setTitle('')
      setAuthor('')
      setIsbn('')
      setBarcode('')
      refresh()
    }
  }

  const placeHold = async (manifestationId: number) => {
    const cc = holdCard.trim().toUpperCase()
    if (!cc) return
    const res = await notify(async () => {
      const hold = await api.placeHold(manifestationId, cc)
      return `Hold #${hold.hold_id} placed for ${hold.patron_card} (queue position ${hold.queue_position})`
    })
    if (res.ok) refresh()
  }

  const changeItemState = async (barcode: string, state: string) => {
    const res = await notify(async () => {
      const it = await api.changeItemState(barcode, state)
      return `Item ${it.barcode} → ${it.state}`
    })
    if (res.ok) refresh()
  }

  const updateWork = async (id: number, t: string, a: string) => {
    const res = await notify(async () => {
      const w = await api.updateWork(id, t, a)
      return `Updated work “${w.title}”`
    })
    if (res.ok) refresh()
    return res.ok
  }

  const updateManifestation = async (
    id: number,
    t: string,
    mat: MaterialType,
    isbn: string,
    pub: string,
  ) => {
    const res = await notify(async () => {
      const m = await api.updateManifestation(id, t, mat, isbn, pub)
      return `Updated manifestation #${m.id}`
    })
    if (res.ok) refresh()
    return res.ok
  }

  const totalCopies = shown.reduce((n, w) => n + copies(w), 0)

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Catalog</h1>
          <div className="sub">Works → manifestations → items</div>
        </div>
        <div className="spacer" />
        <span className="muted mono" style={{ fontSize: 'var(--step--1)' }} data-testid="result-count">
          {shown.length} work{shown.length === 1 ? '' : 's'} · {totalCopies} copies
        </span>
      </header>

      <div className="page">
        <div className="toolbar">
          <form className="scan" onSubmit={(e) => e.preventDefault()}>
            <IconSearch />
            <input
              data-testid="cat-q"
              value={query}
              placeholder="Search title, author or ISBN…"
              autoComplete="off"
              style={{ fontFamily: 'var(--font-body)', fontWeight: 400, letterSpacing: 0, fontSize: 'var(--step-0)' }}
              onChange={(e) => setQuery(e.target.value)}
            />
          </form>
          <div className="seg" role="tablist">
            {FILTERS.map((f) => (
              <button
                key={f}
                role="tab"
                aria-selected={filter === f}
                data-testid={`filter-${f}`}
                onClick={() => setFilter(f)}
              >
                {f === 'audiovisual' ? 'A/V' : f[0].toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
          <label className="row" style={{ gap: 'var(--s2)' }}>
            <span className="muted" style={{ fontSize: 'var(--step--1)' }}>Hold for</span>
            <input
              className="input mono"
              data-testid="hold-card"
              value={holdCard}
              placeholder="C001"
              style={{ width: 110 }}
              onChange={(e) => setHoldCard(e.target.value)}
            />
          </label>
        </div>

        <div className="cat">
          <div className="card">
            <div style={{ overflow: 'auto' }}>
              <table className="tbl">
                <thead>
                  <tr>
                    <th style={{ width: 42 }} />
                    <th>Title</th>
                    <th>Author</th>
                    <th>Editions</th>
                    <th>Copies</th>
                    <th>Available</th>
                  </tr>
                </thead>
                <tbody data-testid="works">
                  {shown.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="muted" style={{ textAlign: 'center', padding: 40 }}>
                        No works yet — catalog one on the right.
                      </td>
                    </tr>
                  ) : (
                    shown.map((w) => {
                      const isOpen = open.has(w.id)
                      const a = avail(w)
                      return (
                        <FragmentRow
                          key={w.id}
                          work={w}
                          isOpen={isOpen}
                          available={a}
                          copies={copies(w)}
                          onToggle={() => toggle(w.id)}
                          onHold={placeHold}
                          onChangeState={changeItemState}
                          onUpdateWork={updateWork}
                          onUpdateManifestation={updateManifestation}
                        />
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <aside className="card" style={{ position: 'sticky', top: 84 }}>
            <div className="card-head">
              <h3>Catalog a title</h3>
            </div>
            <div className="card-pad">
              <div className="row" style={{ gap: 'var(--s2)', marginBottom: 'var(--s4)' }}>
                <span className="chip work">Work</span>
                <span className="muted">→</span>
                <span className="chip manifestation">Manif.</span>
                <span className="muted">→</span>
                <span className="chip item">Item</span>
              </div>
              <form className="flow" onSubmit={submitCatalog}>
                <label className="field">
                  <span className="lbl">Title</span>
                  <input className="input" data-testid="cat-title" value={title} placeholder="Kokoro" onChange={(e) => setTitle(e.target.value)} />
                </label>
                <label className="field">
                  <span className="lbl">Author</span>
                  <input className="input" data-testid="cat-author" value={author} placeholder="Natsume Sōseki" onChange={(e) => setAuthor(e.target.value)} />
                </label>
                <label className="field">
                  <span className="lbl">Material type</span>
                  <select className="select" data-testid="cat-material" value={material} onChange={(e) => setMaterial(e.target.value as MaterialType)}>
                    {MATERIALS.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span className="lbl">ISBN <span className="muted">— optional</span></span>
                  <input className="input mono" data-testid="cat-isbn" value={isbn} placeholder="978-4101010137" onChange={(e) => setIsbn(e.target.value)} />
                </label>
                <label className="field">
                  <span className="lbl">First item barcode</span>
                  <input className="input mono" data-testid="cat-barcode" value={barcode} placeholder="B100" onChange={(e) => setBarcode(e.target.value)} />
                </label>
                <button className="btn" type="submit" data-testid="cat-submit" style={{ width: '100%' }}>
                  <IconPlus />
                  Catalog item
                </button>
              </form>
              <div
                className={msg && !msg.ok ? '' : 'muted'}
                data-testid="cat-msg"
                style={{ fontSize: 'var(--step--1)', marginTop: 'var(--s3)', minHeight: 18, color: msg && !msg.ok ? 'var(--st-lost-fg)' : undefined }}
              >
                {msg?.text ?? ''}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </>
  )
}

function FragmentRow({
  work,
  isOpen,
  available,
  copies,
  onToggle,
  onHold,
  onChangeState,
  onUpdateWork,
  onUpdateManifestation,
}: {
  work: CatalogWork
  isOpen: boolean
  available: number
  copies: number
  onToggle: () => void
  onHold: (manifestationId: number) => void
  onChangeState: (barcode: string, state: string) => void
  onUpdateWork: (id: number, title: string, author: string) => Promise<boolean>
  onUpdateManifestation: (
    id: number,
    title: string,
    material: MaterialType,
    isbn: string,
    publisher: string,
  ) => Promise<boolean>
}) {
  const [editWork, setEditWork] = useState(false)
  const [wTitle, setWTitle] = useState(work.title)
  const [wAuthor, setWAuthor] = useState(work.author)
  const [editManif, setEditManif] = useState<number | null>(null)
  const [mTitle, setMTitle] = useState('')
  const [mMaterial, setMMaterial] = useState<MaterialType>('book')
  const [mIsbn, setMIsbn] = useState('')
  const [mPublisher, setMPublisher] = useState('')

  const startWork = () => {
    setWTitle(work.title)
    setWAuthor(work.author)
    setEditWork(true)
  }
  const saveWork = async () => {
    if (await onUpdateWork(work.id, wTitle, wAuthor)) setEditWork(false)
  }
  const startManif = (m: CatalogWork['manifestations'][number]) => {
    setEditManif(m.id)
    setMTitle(m.title ?? work.title)
    setMMaterial(m.material_type as MaterialType)
    setMIsbn(m.isbn ?? '')
    setMPublisher(m.publisher ?? '')
  }
  const saveManif = async (id: number) => {
    if (await onUpdateManifestation(id, mTitle, mMaterial, mIsbn, mPublisher))
      setEditManif(null)
  }

  return (
    <>
      <tr className={`work-row${isOpen ? ' open' : ''}`} data-testid={`work-${work.id}`} onClick={onToggle}>
        <td>
          <IconChevron className="twist" />
        </td>
        <td>
          <div className="cell-title">{work.title}</div>
          <div className="cell-sub">
            {work.manifestations.length} edition{work.manifestations.length === 1 ? '' : 's'}
          </div>
        </td>
        <td>{work.author}</td>
        <td className="num">{work.manifestations.length}</td>
        <td className="num">{copies}</td>
        <td>
          {available > 0 ? (
            <span className="pill available"><span className="dot" />{available} free</span>
          ) : (
            <span className="pill on_loan"><span className="dot" />none</span>
          )}
        </td>
      </tr>
      {isOpen && (
        <tr className="detail">
          <td />
          <td colSpan={5}>
            <div className="detail-inner">
              <div className="row between" style={{ marginBottom: 'var(--s1)' }}>
                <span className="eyebrow">Work</span>
                <button
                  className="btn btn-ghost btn-sm"
                  data-testid={`work-edit-${work.id}`}
                  onClick={() => (editWork ? setEditWork(false) : startWork())}
                >
                  {editWork ? 'Cancel' : 'Edit work'}
                </button>
              </div>
              {editWork && (
                <div className="row wrap" style={{ gap: 'var(--s2)', marginBottom: 'var(--s3)' }}>
                  <input className="input" data-testid={`work-title-${work.id}`} value={wTitle} onChange={(e) => setWTitle(e.target.value)} style={{ flex: 1, minWidth: 160 }} />
                  <input className="input" data-testid={`work-author-${work.id}`} value={wAuthor} onChange={(e) => setWAuthor(e.target.value)} style={{ flex: 1, minWidth: 140 }} />
                  <button className="btn btn-sm" data-testid={`work-save-${work.id}`} onClick={saveWork}>Save</button>
                </div>
              )}
              {work.manifestations.map((m) => (
                <div className="manif" key={m.id}>
                  <div className="manif-head">
                    {editManif === m.id ? (
                      <>
                        <select className="select" data-testid={`manif-material-${m.id}`} value={mMaterial} onChange={(e) => setMMaterial(e.target.value as MaterialType)} style={{ width: 124 }}>
                          {MATERIALS.map((x) => (
                            <option key={x} value={x}>{x}</option>
                          ))}
                        </select>
                        <input className="input" data-testid={`manif-title-${m.id}`} value={mTitle} onChange={(e) => setMTitle(e.target.value)} placeholder="title" style={{ flex: 1, minWidth: 120 }} />
                        <input className="input mono" data-testid={`manif-isbn-${m.id}`} value={mIsbn} onChange={(e) => setMIsbn(e.target.value)} placeholder="ISBN" style={{ width: 150 }} />
                        <input className="input" data-testid={`manif-publisher-${m.id}`} value={mPublisher} onChange={(e) => setMPublisher(e.target.value)} placeholder="publisher" style={{ width: 130 }} />
                        <button className="btn btn-sm" data-testid={`manif-save-${m.id}`} onClick={() => saveManif(m.id)}>Save</button>
                        <button className="btn btn-secondary btn-sm" onClick={() => setEditManif(null)}>Cancel</button>
                      </>
                    ) : (
                      <>
                        <span className="chip manifestation">{m.material_type}</span>
                        <div style={{ flex: 1 }}>
                          <div className="meta">
                            {m.isbn ? `ISBN ${m.isbn}` : 'no ISBN'} · {m.publisher ?? '—'}
                          </div>
                        </div>
                        <span className="muted mono" style={{ fontSize: 11 }}>manif #{m.id}</span>
                        <button className="btn btn-ghost btn-sm" data-testid={`manif-edit-${m.id}`} onClick={() => startManif(m)}>Edit</button>
                        <button className="btn btn-secondary btn-sm" data-testid={`hold-${m.id}`} onClick={() => onHold(m.id)}>Hold</button>
                      </>
                    )}
                  </div>
                  <div className="copies">
                    {m.items.map((it) => {
                      const actions = STATE_ACTIONS[it.availability]
                      return (
                        <span className="copy" key={it.barcode} data-testid={`copy-${it.barcode}`}>
                          <span className={`dot ${DOT[it.availability] ?? 'dr'}`} />
                          {it.barcode} · {it.availability.replace(/_/g, ' ')}
                          {actions && (
                            <select
                              className="copy-state"
                              data-testid={`copy-state-${it.barcode}`}
                              value=""
                              aria-label={`Change state of ${it.barcode}`}
                              onChange={(e) => {
                                const v = e.target.value
                                e.currentTarget.value = ''
                                if (v) onChangeState(it.barcode, v)
                              }}
                            >
                              <option value="" disabled>
                                change state…
                              </option>
                              {actions.map((a) => (
                                <option key={a.value} value={a.value}>
                                  {a.label}
                                </option>
                              ))}
                            </select>
                          )}
                        </span>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
