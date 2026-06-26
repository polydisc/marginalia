# Marginalia — Frontend

A React + TypeScript (Vite) single-page app for the v1 backend. It carries two
shells, picked by the hash route:

- **Staff console** (`#desk`, `#catalog`) — catalog a book, register a patron,
  run circulation (check out / return / renew / hold), work the hold shelf, and
  look up an item's derived availability.
- **Patron OPAC** (`#/opac`, `#/opac/me`) — the public catalog: search, place a
  hold (card-number sign-in, no password), and a "my library" view of loans and
  holds. Built over the same endpoints; no backend code of its own.

## Architecture

The client only ever calls **same-origin relative paths** (`/works`, `/loans`, …):

- **Production / all-in-one** — `npm run build` emits `dist/`, which the FastAPI
  app serves at `/` (see `backend/app/main.py`). One server, one origin, no CORS.
- **Development** — `npm run dev` runs Vite on `:5173` and proxies the API
  prefixes to the backend on `:8000` (see `vite.config.ts`), so the same relative
  paths work with hot reload.

```text
src/
  api.ts            # typed fetch client; throws ApiError on non-2xx
  types.ts          # response shapes mirroring the backend DTOs
  routes.ts         # hash route -> { shell: staff | opac, screen }
  notify.ts         # Notify type + runApi(); maps failures to {ok,text}
  App.tsx           # thin router: picks StaffShell or OpacShell from the route
  StaffShell.tsx    # staff rail + activity log; wraps calls in notify()
  screens/          # CirculationDesk, Catalog (staff screens)
  opac/             # OpacShell, Browse, MyLibrary, SignIn, useCardSession
  components/       # ActivityLog (+ story)
  icons.tsx
  system.css        # Marginalia design system (shared tokens)
  screens.css       # staff screen styles
  opac.css          # patron-facing OPAC styles
```

## Develop

```sh
# terminal 1 — backend on :8000
cd ../backend && uv run uvicorn app.main:create_app --factory --reload

# terminal 2 — frontend on :5173 (proxies to :8000)
npm install
npm run dev
```

## Build (all-in-one)

```sh
npm run build                       # -> dist/
cd ../backend && uv run uvicorn app.main:create_app --factory   # serves the SPA + API on :8000
# open http://127.0.0.1:8000/
```

## Checks

```sh
npm run typecheck   # tsc --noEmit
npm run test:e2e    # Playwright — builds the SPA, boots uvicorn (all-in-one), drives the flows
```

The first E2E run needs the browser once: `npx playwright install chromium`. The
Playwright config's `webServer` builds `dist/` and starts the backend, so the
suite is self-contained (it just needs the backend deps installed via uv). Both
checks plus backend `pytest` run in CI (`.github/workflows/ci.yml`).

## Storybook

The design system (`system.css`) has a living style guide in Storybook — see
`src/stories/` and the `*.stories.tsx` components.

```sh
npm run storybook        # dev server on http://localhost:6006
npm run build-storybook  # static build to storybook-static/ (also runs in CI)
```

## References

- API + invariants: [../backend/README.md](../backend/README.md)
- Glossary: [../CONTEXT.md](../CONTEXT.md)
- Requirements (incl. OPAC §6): [../SPEC.md](../SPEC.md)
- Design: [../docs/design/0002-v1-backend-catalog-patrons-circulation.md](../docs/design/0002-v1-backend-catalog-patrons-circulation.md)
- OPAC design: [../docs/design/2026-06-26-opac-design.md](../docs/design/2026-06-26-opac-design.md)
