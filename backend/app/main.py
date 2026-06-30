"""FastAPI application factory.

The outermost layer: assembles the app, applies DB migrations for the embedded
SQLite default, and registers routers + the domain-error handlers.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, sessionmaker

from app.adapter.clock import SystemClock
from app.adapter.config import Settings
from app.adapter.db import models  # noqa: F401  (register tables)
from app.adapter.db.engine import make_engine, make_session_factory
from app.adapter.db.migrations import upgrade_to_head
from app.adapter.policy_provider import StaticLoanPolicyProvider
from app.interface.api.errors import add_exception_handlers
from app.interface.api.routers import catalog, circulation, items, patrons

# Built single-page app (all-in-one deploy, ADR 0001). Mounted only if present,
# so the API runs standalone in dev/tests without a frontend build.
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(
    session_factory: sessionmaker[Session] | None = None,
    *,
    settings: Settings | None = None,
) -> FastAPI:
    settings = settings or Settings()
    if session_factory is None:
        # Real-DB path: bring the schema to head via Alembic so a fresh
        # `library.db` is self-contained on `uvicorn app.main:create_app
        # --factory` startup. Tests pass their own session_factory and never
        # reach here, so they keep using create_all (see tests/conftest.py).
        upgrade_to_head(settings.database_url)
        engine = make_engine(settings.database_url)
        session_factory = make_session_factory(engine)

    clock = SystemClock()
    app = FastAPI(title="Marginalia", version="0.1.0")
    app.state.session_factory = session_factory
    app.state.policy_provider = StaticLoanPolicyProvider()
    app.state.clock = clock
    app.state.hold_pickup_window_days = settings.hold_pickup_window_days

    add_exception_handlers(app)
    for module in (catalog, patrons, circulation, items):
        app.include_router(module.router)

    # Serve the SPA last, so the API routes above take precedence over the
    # catch-all static mount. `html=True` returns index.html at `/`.
    if _FRONTEND_DIST.is_dir():
        app.mount(
            "/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="spa"
        )

    return app


# No module-level `app = create_app()`: that would run Alembic at import time
# (e.g. when tests `import create_app`). Boot via the factory instead:
#   uvicorn app.main:create_app --factory
