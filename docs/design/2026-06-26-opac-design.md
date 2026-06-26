# OPAC (patron-facing catalog) — design

**Status:** approved · **Date:** 2026-06-26 · **Author:** igarash1

## Problem

The system today ships only a **staff-facing** console (Marginalia): the
Circulation Desk and the Catalog management screens. There is no patron-facing
experience, so the "user side" of the library cannot be shown or demoed. We want
an **OPAC** (Online Public Access Catalog) — the public interface patrons use to
search the catalog, place holds, and see their own loans and holds.

OPAC was deliberately deferred in v1 (see [SPEC.md](../../SPEC.md) §Scope and
[CONTEXT.md](../../CONTEXT.md) §Access — the term is reserved). This work
delivers it as a thin, patron-facing layer over the existing v1 backend.

## Goals

- A patron can **search/browse** the catalog and see live availability.
- A patron can **place a hold** on an edition (Manifestation).
- A patron can **sign in with a card number** (no password) and see a **My
  Library** page: current loans (with due dates / overdue) and holds (queue
  position, pickup-by), and can **cancel** an open hold.
- The OPAC is visually and structurally **distinct** from the staff console, but
  ships in the **same SPA on the same origin** (no new build, no new deploy).

## Non-goals (YAGNI)

Cover images, faceted search, password authentication, patron self-registration,
internationalisation, and any new patron data fields (e.g. a name). These are
explicitly out of scope.

## Key decision: frontend-only, reuse existing endpoints

Every capability the OPAC needs is already served by the v1 backend. **No backend
code changes.** This keeps the spec/test-locked v1 backend untouched and avoids a
redundant patron-facing search endpoint (client-side filtering over `/catalog` is
what the staff Catalog already does — consistent and sufficient at this scale).

| OPAC capability        | Existing endpoint                          |
| ---------------------- | ------------------------------------------ |
| Search / browse + availability | `GET /catalog`                     |
| Sign in (validate card) | `GET /patrons/{card}`                     |
| Place a hold           | `POST /holds` `{manifestation_id, patron_card}` |
| My Library — loans     | `GET /patrons/{card}/loans`                |
| My Library — holds     | `GET /patrons/{card}/holds`                |
| Cancel a hold          | `POST /holds/{hold_id}/cancel`             |

The hold-cancel path is allowed for an open hold by
[SPEC-HOLD-006](../../SPEC.md); the backend rejects illegal cancels (409),
which the OPAC surfaces as a friendly message.

## Architecture

### Shell split (routing)

The current router (`App.tsx`) reads a single hash segment (`desk` / `catalog`).
We extend it to a **prefix-based shell split**:

- Routes beginning `#/opac` → **OpacShell** (public, patron-facing; no staff rail).
- Everything else (`#desk`, `#catalog`) → **StaffShell** (today's Marginalia
  console, unchanged behaviour).

`App.tsx` shrinks to: own the `notify`/activity-log plumbing it already has, read
the route, and render `StaffShell` or `OpacShell`. The existing rail + `<main>`
move into `StaffShell` verbatim so the staff experience is byte-for-byte the same.

Routes:

| Hash            | Screen                                  |
| --------------- | --------------------------------------- |
| `#/opac`        | Browse / Search                         |
| `#/opac/me`     | My Library (requires a signed-in card)  |

Work detail is an **inline expand** within Browse (mirrors the staff Catalog's
expand pattern), not a separate route — simpler, and keeps a searched result in
context. A deep-link route for a single work is a non-goal for now.

### Units (each independently understandable/testable)

- **`OpacShell`** — patron layout: public header (brand, search affordance,
  sign-in / "C001 · general" + sign-out), renders the active OPAC screen by route.
  Depends on: route, `useCardSession`.
- **`useCardSession`** — a tiny hook owning the signed-in card number, persisted
  in `localStorage`. API: `{ card, signIn(card), signOut() }`. `signIn` validates
  via `GET /patrons/{card}` and rejects (throws / returns error) on 404.
- **`Browse`** (`#/opac`) — loads `/catalog`, client-side search (title / author /
  ISBN) + material filter, renders results as a **public card/grid** with an
  availability badge per work; expanding a work shows its manifestations + a
  **Place hold** action per edition. Depends on: `api.getCatalog`, `api.placeHold`,
  `useCardSession`, `notify`.
- **`MyLibrary`** (`#/opac/me`) — loads loans + holds for the signed-in card;
  shows due dates / overdue badges and holds (queue position, pickup-by) with a
  **Cancel** action. Depends on: `api.patronLoans`, `api.patronHolds`,
  `api.cancelHold`, `useCardSession`.
- **`SignIn`** — card-number entry (modal or inline panel) used when no card is
  set and the patron tries to hold or open My Library.

No new entries are needed in `api.ts` — every method above already exists.

## Behaviour & invariants

- **B-1 · Identity is a card number only.** There is no patron name field in the
  domain (`PatronView` = card_number / category / status / expires_on). The
  signed-in patron is greeted by **card number + category** (e.g. "C001 ·
  general"). No name is invented.
- **B-2 · Sign-in validates the card.** An unknown card (`GET /patrons/{card}` →
  404) is rejected with an inline error; nothing is persisted.
- **B-3 · Session persists.** The signed-in card is kept in `localStorage` and
  restored on reload; sign-out clears it.
- **B-4 · Holding requires a card.** Placing a hold while signed-out prompts
  sign-in first, then proceeds.
- **B-5 · Availability is read-only and live.** The OPAC never writes item state;
  it shows the derived availability from `/catalog` and re-fetches after a hold so
  the badge reflects the change.
- **B-6 · Backend rules are surfaced, not duplicated.** Suspended/expired patrons
  can still browse and view My Library; a rejected hold (422
  `PatronSuspended` / `PatronExpired`) or rejected cancel (409) is shown as a
  friendly message. The OPAC does **not** re-implement these checks.
- **B-7 · Staff experience unchanged.** The StaffShell renders exactly as before;
  the existing circulation e2e suite continues to pass untouched.
- **INV (unchanged) · all-in-one delivery.** OPAC ships in the same SPA served by
  FastAPI on one origin ([SPEC-INV-005](../../SPEC.md)); same-origin relative
  paths only.

## Visual direction

Reuse Marginalia tokens (colour, type, spacing) but present a **public,
book-forward** surface: a card/grid of works with generous spacing and a calm
header — deliberately distinct from the staff console's dense operational tables.
Details (exact grid, hold affordance, empty/sign-in states) are refined in the
implementation phase using the frontend-design skill.

## Documentation & tests (match repo conventions)

This repo is spec-and-test-driven; the OPAC follows suit.

- **SPEC.md** — remove OPAC from the deferred/out-of-scope list and add a new
  **§7 · OPAC** with requirements `SPEC-OPAC-001..00n`, each traced to a test.
- **CONTEXT.md** — update the OPAC glossary entry ("Deferred beyond v1") to note
  it is now delivered as a patron-facing layer over the v1 backend.
- **Playwright e2e** — `frontend/e2e/opac.spec.ts`: sign in with a seeded card →
  search → place a hold → see it on My Library → cancel it. Runs in CI against the
  all-in-one app. Assert the staff suite still passes (no regressions).

## Acceptance criteria

1. Visiting `#/opac` shows the public OPAC shell (no staff rail) and a searchable
   card/grid of the catalog with availability badges.
2. Searching by title / author / ISBN and filtering by material narrows results
   client-side, mirroring the staff Catalog's matching.
3. Signing in with a seeded card persists across reload and greets by card +
   category; an unknown card is rejected inline.
4. A signed-in patron can place a hold on a manifestation; availability re-renders
   and the hold appears on My Library with its queue position.
5. My Library lists current loans (with due date / overdue badge) and holds
   (queue position / pickup-by), and an open hold can be cancelled.
6. A suspended/expired patron sees a friendly backend error when holding, and can
   still browse and view My Library.
7. The existing staff circulation e2e suite passes unchanged; `opac.spec.ts`
   passes in CI.
