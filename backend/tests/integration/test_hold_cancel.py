from __future__ import annotations

from datetime import date

import pytest

from app.adapter.db.models import HoldModel
from app.application.use_cases.circulation import (
    CancelHold,
    CheckIn,
    CheckOut,
    PlaceHold,
)
from app.application.use_cases.patrons import RegisterPatron
from app.domain.errors import HoldNotFound, HoldNotOpen
from app.domain.value_objects import PatronCategory
from tests.conftest import FixedClock, seed

CLOCK = FixedClock(date(2026, 6, 26))


def test_cancel_pending_hold(uow, policy, session_factory):
    s = seed(uow)
    RegisterPatron(uow).execute("C002", PatronCategory.general)
    CheckOut(uow, policy, CLOCK).execute(s.item_barcode, s.patron_card)
    hold = PlaceHold(uow, CLOCK).execute(s.manifestation_id, "C002")

    result = CancelHold(uow, CLOCK, 7).execute(hold.hold_id)
    assert result.status == "cancelled"
    assert result.reassigned == 0
    with session_factory() as session:
        assert session.get(HoldModel, hold.hold_id).status == "cancelled"


def test_cancel_ready_hold_reassigns_to_next(uow, policy, session_factory):
    s = seed(uow)
    RegisterPatron(uow).execute("C002", PatronCategory.general)  # first
    RegisterPatron(uow).execute("C003", PatronCategory.general)  # next
    CheckOut(uow, policy, CLOCK).execute(s.item_barcode, s.patron_card)
    first = PlaceHold(uow, CLOCK).execute(s.manifestation_id, "C002")
    second = PlaceHold(uow, CLOCK).execute(s.manifestation_id, "C003")
    CheckIn(uow, CLOCK, 7).execute(s.item_barcode)  # readies `first`

    result = CancelHold(uow, CLOCK, 7).execute(first.hold_id)
    assert result.reassigned == 1
    with session_factory() as session:
        assert session.get(HoldModel, first.hold_id).status == "cancelled"
        assert session.get(HoldModel, second.hold_id).status == "ready"


def test_cannot_cancel_a_fulfilled_hold(uow, policy, session_factory):
    s = seed(uow)
    RegisterPatron(uow).execute("C002", PatronCategory.general)
    CheckOut(uow, policy, CLOCK).execute(s.item_barcode, s.patron_card)
    hold = PlaceHold(uow, CLOCK).execute(s.manifestation_id, "C002")
    CheckIn(uow, CLOCK, 7).execute(s.item_barcode)  # ready for C002
    CheckOut(uow, policy, CLOCK).execute(s.item_barcode, "C002")  # fulfils it

    with pytest.raises(HoldNotOpen):
        CancelHold(uow, CLOCK, 7).execute(hold.hold_id)


def test_cancel_unknown_hold_raises(uow):
    with pytest.raises(HoldNotFound):
        CancelHold(uow, CLOCK, 7).execute(999)
