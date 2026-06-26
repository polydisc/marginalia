from __future__ import annotations

from dataclasses import dataclass

from app.domain.errors import InvalidItemTransition, ItemNotAvailable
from app.domain.value_objects import ItemState

# Allowed intrinsic-state transitions. `withdrawn` is terminal; "on loan" /
# "on hold shelf" are derived, so they are not states one transitions to.
_ALLOWED_TRANSITIONS: dict[ItemState, frozenset[ItemState]] = {
    ItemState.available: frozenset(
        {ItemState.in_repair, ItemState.lost, ItemState.withdrawn}
    ),
    ItemState.in_repair: frozenset(
        {ItemState.available, ItemState.lost, ItemState.withdrawn}
    ),
    ItemState.lost: frozenset({ItemState.available, ItemState.withdrawn}),
    ItemState.withdrawn: frozenset(),
}


@dataclass
class Item:
    """A single physical copy (FRBR Item), identified by barcode.

    Stores exactly one *intrinsic* state. Whether it is on loan / on the hold
    shelf is derived elsewhere (from Loan / Hold), never stored here.
    References its Manifestation by ID only.
    """

    manifestation_id: int
    barcode: str
    state: ItemState = ItemState.available
    id: int | None = None

    def ensure_intrinsically_loanable(self) -> None:
        """Guard the part of availability the Item itself owns.

        Loan/hold-derived blocking is checked by the use case against the Loan
        and Hold repositories — the Item aggregate does not reach across.
        """
        if self.state is not ItemState.available:
            raise ItemNotAvailable(
                f"item {self.barcode} is {self.state.value}, not available"
            )

    def change_state(self, target: ItemState) -> None:
        """Move the intrinsic state, enforcing the allowed transitions.

        A no-op if already in ``target``. The use case is responsible for the
        cross-aggregate guard (not on loan / not set aside) before taking a copy
        out of circulation.
        """
        if target is self.state:
            return
        if target not in _ALLOWED_TRANSITIONS[self.state]:
            raise InvalidItemTransition(
                f"cannot change item {self.barcode} from "
                f"{self.state.value} to {target.value}"
            )
        self.state = target
