# Python / FastAPI backend with Clean Architecture and SOLID

The backend is built in **Python with FastAPI**, the frontend in
**TypeScript with React**, and the codebase deliberately enforces **Clean
Architecture** (the dependency rule: dependencies point inward, domain entities
know nothing of frameworks) and **SOLID** principles throughout.

This **overrides issue #2**, which originally specified a Java / Spring /
Hibernate backend. The frontend (TS/React) and the "all-in-one app, embedded DB
by default" shape are unchanged.

## Why

- The driving reason for Python/FastAPI is simply that we **want hands-on
  experience with FastAPI** — there is no deeper performance, ecosystem, or
  hiring rationale, and we are recording that honestly so nobody later searches
  for one that does not exist.
- Spring provides DI and layered structure out of the box; FastAPI does not.
  Clean Architecture is therefore adopted as an **explicit, self-imposed
  discipline** rather than a framework freebie — this is what "Clean
  Architecture 徹底" means here. Concretely: domain entities are plain Python
  classes that import neither FastAPI (Pydantic) nor the ORM; Pydantic lives at
  the I/O boundary, the ORM in the adapter layer.
- SOLID is nested inside this: the Dependency-Inversion principle is the
  dependency rule applied at the macro scale; Interface-Segregation keeps
  repositories split by use (e.g. `ItemRepository`, `LoanRepository`) rather
  than one fat data-access object.

## Considered Options

- **Java / Spring / Hibernate** (issue #2's original choice) — rejected in
  favour of the Python stack. Spring would have enforced layering for us, but
  the team wants hands-on experience with FastAPI.

## Consequences

- The team must hold the layering by convention and review, since FastAPI will
  not enforce it. The payoff (framework- and DB-independent domain, unit-
  testable without a running app) only materialises if that discipline holds.
