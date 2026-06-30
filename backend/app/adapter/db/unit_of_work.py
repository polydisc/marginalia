"""SQLAlchemy Unit of Work — the transactional boundary the use cases drive."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.adapter.db.repositories import (
    SqlAlchemyHoldRepository,
    SqlAlchemyItemRepository,
    SqlAlchemyLoanRepository,
    SqlAlchemyManifestationRepository,
    SqlAlchemyPatronRepository,
    SqlAlchemyWorkRepository,
)
from app.domain.repositories import (
    HoldRepository,
    ItemRepository,
    LoanRepository,
    ManifestationRepository,
    PatronRepository,
    WorkRepository,
)


class SqlAlchemyUnitOfWork:
    """Implements the ``UnitOfWork`` port. Opens a fresh Session on enter and
    wires up the repositories against it; commits/rolls back explicitly."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        # Declare the repositories at their port types so this concrete UoW
        # structurally satisfies the ``UnitOfWork`` Protocol (whose attributes
        # are invariant); the SQLAlchemy classes are the adapters behind them.
        self._session: Session = self._session_factory()
        self.works: WorkRepository = SqlAlchemyWorkRepository(self._session)
        self.manifestations: ManifestationRepository = (
            SqlAlchemyManifestationRepository(self._session)
        )
        self.items: ItemRepository = SqlAlchemyItemRepository(self._session)
        self.patrons: PatronRepository = SqlAlchemyPatronRepository(self._session)
        self.loans: LoanRepository = SqlAlchemyLoanRepository(self._session)
        self.holds: HoldRepository = SqlAlchemyHoldRepository(self._session)
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
