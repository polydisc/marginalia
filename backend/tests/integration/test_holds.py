from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.application.use_cases.catalog import AddItem, GetItemAvailability
from app.application.use_cases.circulation import (
    CheckIn,
    CheckOut,
    ExpireReadyHolds,
    PlaceHold,
    RenewLoan,
)
from app.application.use_cases.patrons import RegisterPatron
from app.domain.errors import DuplicateHold, ItemNotAvailable, RenewalBlockedByHold
from app.domain.value_objects import HoldStatus, PatronCategory
from app.infrastructure.db.models import HoldModel
from tests.conftest import FixedClock, seed


def test_checkin_assigns_returned_item_to_queue_head(uow, policy, clock):
    s = seed(uow)  # patron C001
    RegisterPatron(uow).execute("C002", PatronCategory.general)

    CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)
    hold = PlaceHold(uow, clock).execute(s.manifestation_id, "C002")
    assert hold.queue_position == 1
    assert hold.status == "pending"

    result = CheckIn(uow, clock, 7).execute(s.item_barcode)
    assert result.hold_triggered is True
    assert result.ready_hold_id == hold.hold_id

    # Item is intrinsically available but set aside -> derived on_hold_shelf.
    avail = GetItemAvailability(uow).execute(s.item_barcode)
    assert avail.intrinsic_state == "available"
    assert avail.availability == "on_hold_shelf"


def test_held_item_cannot_be_taken_by_another_patron(uow, policy, clock):
    s = seed(uow)
    RegisterPatron(uow).execute("C002", PatronCategory.general)  # holder
    RegisterPatron(uow).execute("C003", PatronCategory.general)  # walk-in

    CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)
    PlaceHold(uow, clock).execute(s.manifestation_id, "C002")
    CheckIn(uow, clock, 7).execute(s.item_barcode)  # now set aside for C002

    with pytest.raises(ItemNotAvailable):
        CheckOut(uow, policy, clock).execute(s.item_barcode, "C003")


def test_hold_owner_can_check_out_and_fulfills_hold(
    uow, policy, clock, session_factory
):
    s = seed(uow)
    RegisterPatron(uow).execute("C002", PatronCategory.general)

    CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)
    hold = PlaceHold(uow, clock).execute(s.manifestation_id, "C002")
    CheckIn(uow, clock, 7).execute(s.item_barcode)  # set aside for C002

    loan = CheckOut(uow, policy, clock).execute(s.item_barcode, "C002")
    assert loan.patron_card == "C002"
    # Item is now on loan to the hold owner...
    assert (
        GetItemAvailability(uow).execute(s.item_barcode).availability
        == "on_loan"
    )
    # ...and the hold has been marked fulfilled.
    with session_factory() as session:
        assert session.get(HoldModel, hold.hold_id).status == (
            HoldStatus.fulfilled.value
        )


def test_pending_hold_blocks_renewal(uow, policy, clock):
    s = seed(uow)
    RegisterPatron(uow).execute("C002", PatronCategory.general)

    CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)
    PlaceHold(uow, clock).execute(s.manifestation_id, "C002")

    with pytest.raises(RenewalBlockedByHold):
        RenewLoan(uow, policy, clock).execute(s.item_barcode)


def test_patron_cannot_stack_duplicate_open_holds(uow, clock):
    s = seed(uow)

    PlaceHold(uow, clock).execute(s.manifestation_id, s.patron_card)
    with pytest.raises(DuplicateHold):
        PlaceHold(uow, clock).execute(s.manifestation_id, s.patron_card)


def test_open_hold_unique_index_is_the_concurrency_backstop(session_factory):
    """The DB rejects a duplicate open hold even if application code is bypassed,
    but permits a new hold after the previous one is no longer open."""
    with session_factory() as session:
        session.add(
            HoldModel(
                manifestation_id=1,
                patron_id=1,
                placed_at=datetime(2026, 6, 26, 12),
                queue_position=1,
                status="pending",
            )
        )
        session.commit()

    with session_factory() as session:
        session.add(
            HoldModel(
                manifestation_id=1,
                patron_id=1,
                placed_at=datetime(2026, 6, 26, 12),
                queue_position=2,
                status="pending",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    with session_factory() as session:
        first = session.get(HoldModel, 1)
        first.status = "cancelled"
        session.commit()
        session.add(
            HoldModel(
                manifestation_id=1,
                patron_id=1,
                placed_at=datetime(2026, 6, 27, 12),
                queue_position=3,
                status="pending",
            )
        )
        session.commit()  # no error: only pending/ready holds are unique


def test_unclaimed_ready_hold_expires_and_item_returns_to_shelf(uow, policy):
    clock = FixedClock(date(2026, 6, 26))
    s = seed(uow)
    RegisterPatron(uow).execute("C002", PatronCategory.general)

    CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)
    PlaceHold(uow, clock).execute(s.manifestation_id, "C002")
    CheckIn(uow, clock, 7).execute(s.item_barcode)  # pickup_by = 2026-07-03
    assert (
        GetItemAvailability(uow).execute(s.item_barcode).availability
        == "on_hold_shelf"
    )

    # Nobody collects; sweep a day after the pickup window.
    late = FixedClock(date(2026, 7, 4))
    result = ExpireReadyHolds(uow, late, 7).execute()
    assert result.expired == 1
    assert result.reassigned == 0
    # No ready hold remains, so the copy is available again.
    assert (
        GetItemAvailability(uow).execute(s.item_barcode).availability
        == "available"
    )


def test_expired_hold_is_reassigned_to_next_in_queue(uow, policy):
    clock = FixedClock(date(2026, 6, 26))
    s = seed(uow)
    RegisterPatron(uow).execute("C002", PatronCategory.general)  # first in line
    RegisterPatron(uow).execute("C003", PatronCategory.general)  # next in line

    CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)
    PlaceHold(uow, clock).execute(s.manifestation_id, "C002")
    PlaceHold(uow, clock).execute(s.manifestation_id, "C003")
    CheckIn(uow, clock, 7).execute(s.item_barcode)  # readied for C002

    result = ExpireReadyHolds(uow, FixedClock(date(2026, 7, 4)), 7).execute()
    assert result.expired == 1
    assert result.reassigned == 1
    # The copy is handed to C003, still set aside (not back on the shelf).
    assert (
        GetItemAvailability(uow).execute(s.item_barcode).availability
        == "on_hold_shelf"
    )


def test_two_ready_holds_expire_with_one_waiter_no_double_assign(uow, policy):
    """Two copies readied for two holders; both expire in one sweep while a
    single patron waits. Exactly one copy is reassigned, the other re-shelved —
    the queue head must not be assigned twice."""
    clock = FixedClock(date(2026, 6, 26))
    s = seed(uow)  # manifestation M, item B001, patron C001
    AddItem(uow).execute(s.manifestation_id, "B002")  # second copy
    for card in ("C002", "C003", "C004", "C005"):
        RegisterPatron(uow).execute(card, PatronCategory.general)

    # Both copies out.
    CheckOut(uow, policy, clock).execute("B001", s.patron_card)
    CheckOut(uow, policy, clock).execute("B002", "C002")
    # Three patrons queue on the manifestation.
    PlaceHold(uow, clock).execute(s.manifestation_id, "C003")
    PlaceHold(uow, clock).execute(s.manifestation_id, "C004")
    PlaceHold(uow, clock).execute(s.manifestation_id, "C005")
    # Returns ready the two queue heads (C003 -> B001, C004 -> B002).
    CheckIn(uow, clock, 7).execute("B001")
    CheckIn(uow, clock, 7).execute("B002")

    result = ExpireReadyHolds(uow, FixedClock(date(2026, 7, 4)), 7).execute()
    assert result.expired == 2
    # Only C005 is left waiting -> exactly one copy reassigned, the other freed.
    assert result.reassigned == 1
    availabilities = sorted(
        GetItemAvailability(uow).execute(b).availability
        for b in ("B001", "B002")
    )
    assert availabilities == ["available", "on_hold_shelf"]
