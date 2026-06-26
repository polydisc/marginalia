from __future__ import annotations

from datetime import date, datetime

from app.domain.entities import Hold, Item, Loan
from app.domain.services import AvailabilityService
from app.domain.value_objects import Availability, HoldStatus, ItemState

svc = AvailabilityService()


def _item(state: ItemState = ItemState.available) -> Item:
    return Item(manifestation_id=1, barcode="B001", state=state, id=1)


def _open_loan() -> Loan:
    return Loan(
        item_id=1,
        patron_id=1,
        loaned_at=datetime(2026, 6, 1, 12),
        due_date=date(2026, 6, 30),
    )


def _ready_hold() -> Hold:
    return Hold(
        manifestation_id=1,
        patron_id=2,
        placed_at=datetime(2026, 6, 1, 12),
        queue_position=1,
        status=HoldStatus.ready,
        assigned_item_id=1,
    )


def test_available_when_nothing_blocks():
    assert svc.availability_of(_item(), None, None) is Availability.available
    assert svc.is_loanable(_item(), None, None)


def test_open_loan_derives_on_loan():
    assert (
        svc.availability_of(_item(), _open_loan(), None)
        is Availability.on_loan
    )
    assert not svc.is_loanable(_item(), _open_loan(), None)


def test_ready_hold_derives_on_hold_shelf():
    assert (
        svc.availability_of(_item(), None, _ready_hold())
        is Availability.on_hold_shelf
    )


def test_intrinsic_state_wins_over_derived():
    # A lost item is lost even if a stale loan row existed.
    assert (
        svc.availability_of(_item(ItemState.lost), _open_loan(), None)
        is Availability.lost
    )
