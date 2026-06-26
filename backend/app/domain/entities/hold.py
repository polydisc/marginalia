from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.domain.errors import HoldNotOpen, HoldNotPending, HoldNotReady
from app.domain.value_objects import HoldStatus


@dataclass
class Hold:
    """A Patron's request to borrow a Manifestation (a specific edition).

    Placed against a Manifestation, fulfilled by an Item on check-in. An
    independent aggregate referencing Patron and Manifestation by ID.
    """

    manifestation_id: int
    patron_id: int
    placed_at: datetime
    queue_position: int
    status: HoldStatus = HoldStatus.pending
    assigned_item_id: int | None = None
    pickup_by: date | None = None
    id: int | None = None

    def assign_item(self, item_id: int, pickup_by: date) -> None:
        """Set aside a returned Item for this hold (queue head, on check-in).

        ``pickup_by`` is the last day the patron may collect it before the hold
        expires and the copy moves on.
        """
        if self.status is not HoldStatus.pending:
            raise HoldNotPending(
                f"hold {self.id} is {self.status.value}, not pending"
            )
        self.status = HoldStatus.ready
        self.assigned_item_id = item_id
        self.pickup_by = pickup_by

    def fulfill(self) -> None:
        """The waiting patron has checked the assigned item out."""
        if self.status is not HoldStatus.ready:
            raise HoldNotReady(f"hold {self.id} is not ready to fulfill")
        self.status = HoldStatus.fulfilled

    def expire(self) -> None:
        """The pickup-by date has passed without collection."""
        if self.status is not HoldStatus.ready:
            raise HoldNotReady(f"hold {self.id} is not ready to expire")
        self.status = HoldStatus.expired
        # assigned_item_id / pickup_by are kept as an audit trail of which copy
        # was set aside; availability is derived from `status`, so they are inert
        # once expired (an expired hold never matches get_ready_for_item).

    def cancel(self) -> None:
        """Cancel an open hold (still pending in the queue, or ready for pickup).

        A fulfilled / expired / already-cancelled hold cannot be cancelled.
        """
        if self.status not in (HoldStatus.pending, HoldStatus.ready):
            raise HoldNotOpen(
                f"hold {self.id} is {self.status.value}; cannot cancel"
            )
        self.status = HoldStatus.cancelled
