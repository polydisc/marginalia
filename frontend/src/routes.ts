/**
 * Hash-route model. Two shells share one SPA: the staff console (Circulation
 * Desk / Catalog) and the patron-facing OPAC. The shell is chosen by the hash
 * prefix — `#/opac…` is public, everything else is staff.
 */
export type StaffRoute = { shell: 'staff'; screen: 'desk' | 'catalog' }
export type OpacRoute = { shell: 'opac'; screen: 'browse' | 'me' }
export type Route = StaffRoute | OpacRoute

export function parseRoute(hash: string): Route {
  const h = hash.replace(/^#/, '')
  if (h === '/opac/me') return { shell: 'opac', screen: 'me' }
  if (h === '/opac' || h.startsWith('/opac/')) return { shell: 'opac', screen: 'browse' }
  if (h === 'catalog') return { shell: 'staff', screen: 'catalog' }
  return { shell: 'staff', screen: 'desk' }
}

/** Navigate by writing the hash; the shells re-render on `hashchange`. */
export function navigate(hash: string): void {
  window.location.hash = hash
}
