import { useEffect, useState } from 'react'
import { parseRoute, type Route } from './routes'
import { StaffShell } from './StaffShell'
import { OpacShell } from './opac/OpacShell'

function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash))
  useEffect(() => {
    const on = () => setRoute(parseRoute(window.location.hash))
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return route
}

/** Picks the shell from the route: the patron OPAC or the staff console. */
export function App() {
  const route = useHashRoute()
  return route.shell === 'opac' ? (
    <OpacShell route={route} />
  ) : (
    <StaffShell route={route} />
  )
}
