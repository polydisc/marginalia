"""Read-side query port.

Projections for the UI that intentionally bypass the write aggregates (a hold
shelf, a patron's loans, the catalog tree). Implemented in the adapter ring with
joins; the interface depends only on this abstraction.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.application.dto import (
    CatalogWorkView,
    LoanLineView,
    PatronHoldView,
    PatronView,
    ReadyHoldView,
)


class QueryService(Protocol):
    def catalog(self) -> Sequence[CatalogWorkView]: ...

    def patron(self, card_number: str) -> PatronView | None: ...

    def patron_loans(self, card_number: str) -> Sequence[LoanLineView]: ...

    def patron_holds(self, card_number: str) -> Sequence[PatronHoldView]: ...

    def ready_holds(self) -> Sequence[ReadyHoldView]: ...
