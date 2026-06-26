from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.domain.errors import LoanNotOpen, RenewalLimitReached


@dataclass
class Loan:
    """The record of one Item lent to one Patron.

    An independent aggregate (ADR 0003): references Item and Patron by ID only.
    "On loan" is the existence of an *open* Loan (``returned_at is None``) — it
    is never stored as a flag on the Item.
    """

    item_id: int
    patron_id: int
    loaned_at: datetime
    due_date: date
    returned_at: datetime | None = None
    renewal_count: int = 0
    id: int | None = None

    @property
    def is_open(self) -> bool:
        return self.returned_at is None

    def is_overdue(self, on: date) -> bool:
        return self.is_open and self.due_date < on

    def renew(self, renewal_limit: int, new_due_date: date) -> None:
        if not self.is_open:
            raise LoanNotOpen("cannot renew a returned loan")
        if self.renewal_count >= renewal_limit:
            raise RenewalLimitReached(
                f"renewal limit ({renewal_limit}) reached"
            )
        self.renewal_count += 1
        self.due_date = new_due_date

    def close(self, returned_at: datetime) -> None:
        if not self.is_open:
            raise LoanNotOpen("loan is already closed")
        self.returned_at = returned_at
