"""Repository ports (Protocols).

Dependency-Inversion (SOLID-D): the application depends on these abstractions;
concrete SQLAlchemy implementations live in infrastructure. Interface-
Segregation (SOLID-I): one focused repository per aggregate, not a fat DAO.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from app.domain.entities import (
    Hold,
    Item,
    Loan,
    Manifestation,
    Patron,
    Work,
)


class WorkRepository(Protocol):
    def add(self, work: Work) -> Work: ...

    def update(self, work: Work) -> None: ...

    def get(self, work_id: int) -> Work | None: ...


class ManifestationRepository(Protocol):
    def add(self, manifestation: Manifestation) -> Manifestation: ...

    def update(self, manifestation: Manifestation) -> None: ...

    def get(self, manifestation_id: int) -> Manifestation | None: ...


class ItemRepository(Protocol):
    def add(self, item: Item) -> Item: ...

    def get(self, item_id: int) -> Item | None: ...

    def get_by_barcode(self, barcode: str) -> Item | None: ...

    def update(self, item: Item) -> None: ...


class PatronRepository(Protocol):
    def add(self, patron: Patron) -> Patron: ...

    def update(self, patron: Patron) -> None: ...

    def get(self, patron_id: int) -> Patron | None: ...

    def get_by_card_number(self, card_number: str) -> Patron | None: ...


class LoanRepository(Protocol):
    def add(self, loan: Loan) -> Loan: ...

    def update(self, loan: Loan) -> None: ...

    def get_open_by_item(self, item_id: int) -> Loan | None: ...

    def list_open_by_patron(self, patron_id: int) -> Sequence[Loan]: ...


class HoldRepository(Protocol):
    def add(self, hold: Hold) -> Hold: ...

    def update(self, hold: Hold) -> None: ...

    def get(self, hold_id: int) -> Hold | None: ...

    def list_pending_by_manifestation(
        self, manifestation_id: int
    ) -> Sequence[Hold]:
        """Pending holds, ordered by queue position (head first)."""
        ...

    def get_ready_for_item(self, item_id: int) -> Hold | None:
        """The ready hold an item has been set aside for, if any."""
        ...

    def get_open_by_patron_and_manifestation(
        self, patron_id: int, manifestation_id: int
    ) -> Hold | None:
        """An open hold this patron already has for the manifestation."""
        ...

    def list_ready_expired(self, on: date) -> Sequence[Hold]:
        """Ready holds whose pickup-by date has passed (``pickup_by < on``)."""
        ...

    def next_queue_position(self, manifestation_id: int) -> int: ...
