import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { runApi, type Result } from '../notify'
import type { CatalogWork, MaterialType } from '../types'
import { IconSearch } from '../icons'
import type { CardSession } from './useCardSession'

const FILTERS: ('all' | MaterialType)[] = ['all', 'book', 'reference', 'audiovisual']
const MATERIAL_LABEL: Record<string, string> = {
  book: 'Book',
  reference: 'Reference',
  audiovisual: 'A/V',
}

const availableCopies = (m: CatalogWork['manifestations'][number]) =>
  m.items.filter((i) => i.availability === 'available').length

/** The public catalogue: search, browse, and place a hold on an edition. */
export function Browse({
  session,
  onNeedSignIn,
}: {
  session: CardSession
  onNeedSignIn: () => void
}) {
  const [works, setWorks] = useState<CatalogWork[]>([])
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<'all' | MaterialType>('all')
  const [msg, setMsg] = useState<Result | null>(null)

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

  const placeHold = async (manifestationId: number, title: string) => {
    if (!session.patron) {
      onNeedSignIn()
      return
    }
    const res = await runApi(async () => {
      const hold = await api.placeHold(manifestationId, session.patron!.card_number)
      return `Hold placed on “${title}” — you're #${hold.queue_position} in the queue.`
    })
    setMsg(res)
  }

  const totalCopies = shown.reduce(
    (n, w) => n + w.manifestations.reduce((k, m) => k + m.items.length, 0),
    0,
  )

  return (
    <div className="opac-page">
      <div className="opac-hero">
        <h1 className="serif">Find your next read</h1>
        <p className="muted">Search the library catalogue and reserve a copy.</p>
        <form className="opac-search" onSubmit={(e) => e.preventDefault()}>
          <IconSearch />
          <input
            data-testid="opac-q"
            value={query}
            placeholder="Search by title, author or ISBN…"
            autoComplete="off"
            onChange={(e) => setQuery(e.target.value)}
          />
        </form>
        <div className="opac-filters" role="tablist">
          {FILTERS.map((f) => (
            <button
              key={f}
              role="tab"
              aria-selected={filter === f}
              data-testid={`opac-filter-${f}`}
              className={filter === f ? 'active' : ''}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? 'All' : MATERIAL_LABEL[f]}
            </button>
          ))}
        </div>
      </div>

      <div className="opac-results-head">
        <span data-testid="opac-result-count">
          {shown.length} title{shown.length === 1 ? '' : 's'} · {totalCopies} copies
        </span>
        {msg && (
          <span
            className={msg.ok ? 'opac-flash ok' : 'opac-flash err'}
            data-testid="opac-flash"
          >
            {msg.text}
          </span>
        )}
      </div>

      {shown.length === 0 ? (
        <div className="opac-empty" data-testid="opac-empty">
          No titles match your search.
        </div>
      ) : (
        <div className="opac-grid" data-testid="opac-works">
          {shown.map((w) => {
            const copies = w.manifestations.reduce((n, m) => n + m.items.length, 0)
            const free = w.manifestations.reduce((n, m) => n + availableCopies(m), 0)
            return (
              <article className="book-card" key={w.id} data-testid={`opac-work-${w.id}`}>
                <div className="book-spine" aria-hidden="true">
                  {w.title.slice(0, 1).toUpperCase()}
                </div>
                <div className="book-body">
                  <h3 className="serif book-title">{w.title}</h3>
                  <div className="book-author">{w.author}</div>
                  <div className="book-avail">
                    <span className={`pill ${free > 0 ? 'available' : 'on_loan'}`}>
                      <span className="dot" />
                      {free > 0 ? `${free} of ${copies} available` : 'all copies out'}
                    </span>
                  </div>
                  <ul className="edition-list">
                    {w.manifestations.map((m) => {
                      const editionFree = availableCopies(m)
                      return (
                        <li className="edition" key={m.id}>
                          <div className="edition-meta">
                            <span className="chip manifestation">
                              {MATERIAL_LABEL[m.material_type] ?? m.material_type}
                            </span>
                            <span className="muted mono edition-isbn">
                              {m.isbn ? m.isbn : 'no ISBN'}
                            </span>
                          </div>
                          <div className="edition-actions">
                            <span className="muted edition-free">
                              {editionFree > 0 ? `${editionFree} available` : 'on loan'}
                            </span>
                            <button
                              className="btn btn-sm"
                              data-testid={`opac-hold-${m.id}`}
                              onClick={() => placeHold(m.id, w.title)}
                            >
                              Place hold
                            </button>
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
