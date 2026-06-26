import { useCallback, useState } from 'react'
import { ApiError } from './api'
import { IconCatalog, IconCirc } from './icons'
import { navigate, type StaffRoute } from './routes'
import type { Notify } from './notify'
import { CirculationDesk } from './screens/CirculationDesk'
import { Catalog } from './screens/Catalog'
import type { LogEntry } from './components/ActivityLog'

let seq = 0

/** The operational console: left rail + the active staff screen. */
export function StaffShell({ route }: { route: StaffRoute }) {
  const [log, setLog] = useState<LogEntry[]>([])

  const push = useCallback((kind: LogEntry['kind'], text: string) => {
    setLog((prev) => [{ id: ++seq, kind, text, at: new Date() }, ...prev].slice(0, 40))
  }, [])

  const notify = useCallback<Notify>(
    async (run) => {
      try {
        const text = await run()
        push('ok', text)
        return { ok: true, text }
      } catch (err) {
        if (err instanceof ApiError) {
          const text = `${err.status} ${err.code}: ${err.message}`
          push('err', text)
          return { ok: false, text }
        }
        // Network / unexpected: keep the log clean, detail to the console.
        console.error(err)
        const text = 'Network error — please retry'
        push('err', text)
        return { ok: false, text }
      }
    },
    [push],
  )

  return (
    <div className="app">
      <aside className="rail">
        <div className="brand">
          <div className="brand-mark">M</div>
          <div>
            <div className="brand-name">Marginalia</div>
            <div className="brand-sub">
              {route.screen === 'desk' ? 'Circulation' : 'Catalog'}
            </div>
          </div>
        </div>
        <nav className="nav">
          <div className="nav-label">Library</div>
          <button
            className={`navlink${route.screen === 'desk' ? ' active' : ''}`}
            data-testid="nav-desk"
            onClick={() => navigate('desk')}
          >
            <IconCirc />
            Circulation
          </button>
          <button
            className={`navlink${route.screen === 'catalog' ? ' active' : ''}`}
            data-testid="nav-catalog"
            onClick={() => navigate('catalog')}
          >
            <IconCatalog />
            Catalog
          </button>
          <div className="nav-label">Public</div>
          <button
            className="navlink"
            data-testid="nav-opac"
            onClick={() => navigate('/opac')}
          >
            <IconSearchNav />
            Open OPAC
          </button>
        </nav>
        <div className="rail-foot">
          <div className="avatar">LS</div>
          <div style={{ fontSize: 'var(--step--1)' }}>
            <div style={{ fontWeight: 600 }}>Lillian Simmons</div>
            <div className="muted">Circulation staff</div>
          </div>
        </div>
      </aside>

      <main className="content">
        {route.screen === 'desk' ? (
          <CirculationDesk notify={notify} log={log} />
        ) : (
          <Catalog notify={notify} />
        )}
      </main>
    </div>
  )
}

function IconSearchNav() {
  return (
    <svg className="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.2-3.2" />
    </svg>
  )
}
