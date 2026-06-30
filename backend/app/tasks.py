"""Maintenance tasks runnable from cron / a scheduler (outside the web app).

Run the hold-expiry sweep against the configured database:

    cd backend && uv run python -m app.tasks

Schedule it daily, e.g. crontab:

    0 2 * * *  cd /path/to/backend && uv run python -m app.tasks >> expire.log 2>&1
"""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.adapter.clock import SystemClock
from app.adapter.config import Settings
from app.adapter.db.engine import make_engine, make_session_factory
from app.adapter.db.unit_of_work import SqlAlchemyUnitOfWork
from app.application.dto import ExpireHoldsResult
from app.application.use_cases.circulation import ExpireReadyHolds


def run_expire_holds(
    session_factory: sessionmaker[Session] | None = None,
    *,
    settings: Settings | None = None,
) -> ExpireHoldsResult:
    """Expire ready holds past their pickup-by date. Reuses the same use case
    the API exposes at POST /holds/expire."""
    settings = settings or Settings()
    engine = None
    if session_factory is None:
        engine = make_engine(settings.database_url)
        session_factory = make_session_factory(engine)
    try:
        return ExpireReadyHolds(
            SqlAlchemyUnitOfWork(session_factory),
            SystemClock(),
            settings.hold_pickup_window_days,
        ).execute()
    finally:
        # Dispose only an engine we created here (not a caller-supplied factory).
        if engine is not None:
            engine.dispose()


def main() -> None:  # pragma: no cover - thin CLI wrapper
    result = run_expire_holds()
    print(f"expired={result.expired} reassigned={result.reassigned}")


if __name__ == "__main__":  # pragma: no cover
    main()
