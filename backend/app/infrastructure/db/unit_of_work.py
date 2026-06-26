"""SQLAlchemy Unit of Work — the transactional boundary the use cases drive."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.repositories import (
    SqlAlchemyHoldRepository,
    SqlAlchemyItemRepository,
    SqlAlchemyLoanRepository,
    SqlAlchemyManifestationRepository,
    SqlAlchemyPatronRepository,
    SqlAlchemyWorkRepository,
)


class SqlAlchemyUnitOfWork:
    """Implements the ``UnitOfWork`` port. Opens a fresh Session on enter and
    wires up the repositories against it; commits/rolls back explicitly."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self._session: Session = self._session_factory()
        self.works = SqlAlchemyWorkRepository(self._session)
        self.manifestations = SqlAlchemyManifestationRepository(self._session)
        self.items = SqlAlchemyItemRepository(self._session)
        self.patrons = SqlAlchemyPatronRepository(self._session)
        self.loans = SqlAlchemyLoanRepository(self._session)
        self.holds = SqlAlchemyHoldRepository(self._session)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # Anything not explicitly committed is discarded: close() rolls back the
        # open transaction, so read-only use cases (no commit) leave no trace and
        # a forgotten commit fails loudly in tests rather than silently persisting.
        if exc_type is not None:
            self.rollback()
        self._session.close()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
