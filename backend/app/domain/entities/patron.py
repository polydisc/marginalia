from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.domain.entities.loan import Loan
from app.domain.errors import (
    PatronCannotBorrow,
    PatronExpired,
    PatronSuspended,
)
from app.domain.value_objects import PatronCategory, PatronStatus


@dataclass
class Patron:
    """A person holding borrowing privileges.

    A core domain entity that carries its own borrowing rules and lifecycle
    (active/suspended, an optional card expiry). References nothing about
    authentication — a Patron typically has no system login.
    """

    card_number: str
    category: PatronCategory
    status: PatronStatus = PatronStatus.active
    expires_on: date | None = None
    id: int | None = None

    def is_expired(self, today: date) -> bool:
        # `expires_on` is the last valid day; expired only once it is past.
        return self.expires_on is not None and today > self.expires_on

    def suspend(self) -> None:
        self.status = PatronStatus.suspended

    def reinstate(self) -> None:
        self.status = PatronStatus.active

    def ensure_active(self, today: date) -> None:
        """Raise if the account itself bars borrowing (suspended / expired)."""
        if self.status is PatronStatus.suspended:
            raise PatronSuspended(
                f"patron {self.card_number} is suspended"
            )
        if self.is_expired(today):
            raise PatronExpired(
                f"patron {self.card_number}'s card expired on {self.expires_on}"
            )

    def ensure_can_borrow(
        self,
        open_loans: Sequence[Loan],
        max_concurrent_loans: int,
        today: date,
    ) -> None:
        """Raise if this patron may not take on another loan.

        Blocked when suspended/expired, when holding any overdue loan
        (CONTEXT.md: overdue blocks borrowing, no money modeled), or when
        already at the concurrent-loan limit set by policy.
        """
        self.ensure_active(today)
        if any(loan.is_overdue(today) for loan in open_loans):
            raise PatronCannotBorrow(
                f"patron {self.card_number} has overdue loans"
            )
        if len(open_loans) >= max_concurrent_loans:
            raise PatronCannotBorrow(
                f"patron {self.card_number} is at the loan limit "
                f"({max_concurrent_loans})"
            )
