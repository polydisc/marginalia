"""Unit-of-Work port.

One transactional boundary that exposes the repositories the use cases need.
Concrete implementation (SQLAlchemy) lives in the adapter ring; use cases depend
only on this abstraction.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.repositories import (
    HoldRepository,
    ItemRepository,
    LoanRepository,
    ManifestationRepository,
    PatronRepository,
    WorkRepository,
)


class UnitOfWork(Protocol):
    works: WorkRepository
    manifestations: ManifestationRepository
    items: ItemRepository
    patrons: PatronRepository
    loans: LoanRepository
    holds: HoldRepository

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(self, exc_type, exc, tb) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
