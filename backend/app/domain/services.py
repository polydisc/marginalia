"""Domain services — logic that spans aggregates without owning state."""

from __future__ import annotations

from app.domain.entities import Hold, Item, Loan
from app.domain.value_objects import Availability, ItemState


class AvailabilityService:
    """Compose an Item's *derived* availability (CONTEXT.md).

    The Item aggregate cannot answer this alone — it must be told about the
    relevant open Loan / ready Hold (read across aggregates is allowed).
    """

    def availability_of(
        self,
        item: Item,
        open_loan: Loan | None,
        ready_hold: Hold | None,
    ) -> Availability:
        if item.state is ItemState.in_repair:
            return Availability.in_repair
        if item.state is ItemState.lost:
            return Availability.lost
        if item.state is ItemState.withdrawn:
            return Availability.withdrawn
        # intrinsic state is `available` — layer the derived states on top
        if open_loan is not None:
            return Availability.on_loan
        if ready_hold is not None:
            return Availability.on_hold_shelf
        return Availability.available

    def is_loanable(
        self,
        item: Item,
        open_loan: Loan | None,
        ready_hold: Hold | None,
    ) -> bool:
        return (
            self.availability_of(item, open_loan, ready_hold)
            is Availability.available
        )
