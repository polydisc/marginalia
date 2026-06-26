import { useCallback, useState } from 'react'
import { navigate, type OpacRoute } from '../routes'
import { Browse } from './Browse'
import { MyLibrary } from './MyLibrary'
import { SignIn } from './SignIn'
import { useCardSession } from './useCardSession'
import '../opac.css'

/** The patron-facing public shell: a calm header + the active OPAC screen. */
export function OpacShell({ route }: { route: OpacRoute }) {
  const session = useCardSession()
  const [showSignIn, setShowSignIn] = useState(false)
  const requireSignIn = useCallback(() => setShowSignIn(true), [])

  return (
    <div className="opac">
      <header className="opac-top">
        <button className="opac-brand" onClick={() => navigate('/opac')}>
          <span className="opac-brand-mark">M</span>
          <span>
            <span className="opac-brand-name">Marginalia</span>
            <span className="opac-brand-sub">Public catalogue</span>
          </span>
        </button>

        <nav className="opac-nav">
          <button
            className={route.screen === 'browse' ? 'active' : ''}
            data-testid="opac-nav-browse"
            onClick={() => navigate('/opac')}
          >
            Browse
          </button>
          <button
            className={route.screen === 'me' ? 'active' : ''}
            data-testid="opac-nav-me"
            onClick={() => navigate('/opac/me')}
          >
            My library
          </button>
        </nav>

        <div className="opac-account">
          {session.patron ? (
            <>
              <span className="opac-whoami" data-testid="opac-whoami">
                {session.patron.card_number} · {session.patron.category}
              </span>
              <button
                className="btn btn-ghost btn-sm"
                data-testid="opac-signout"
                onClick={session.signOut}
              >
                Sign out
              </button>
            </>
          ) : (
            <button
              className="btn btn-sm"
              data-testid="opac-signin"
              onClick={requireSignIn}
            >
              Sign in
            </button>
          )}
          <a className="opac-staff-link" data-testid="opac-staff-link" href="#desk">
            Staff
          </a>
        </div>
      </header>

      <main className="opac-main">
        {route.screen === 'me' ? (
          <MyLibrary session={session} onSignIn={requireSignIn} />
        ) : (
          <Browse session={session} onNeedSignIn={requireSignIn} />
        )}
      </main>

      {showSignIn && <SignIn session={session} onClose={() => setShowSignIn(false)} />}
    </div>
  )
}
