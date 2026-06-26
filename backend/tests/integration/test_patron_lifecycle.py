from __future__ import annotations

from datetime import date

import pytest

from app.application.use_cases.circulation import (
    CheckOut,
    PlaceHold,
    RenewLoan,
)
from app.application.use_cases.patrons import (
    RegisterPatron,
    ReinstatePatron,
    SuspendPatron,
)
from app.domain.errors import PatronExpired, PatronSuspended
from app.domain.value_objects import PatronCategory
from tests.conftest import seed


def test_expired_card_blocks_checkout(uow, policy, clock):
    s = seed(uow)  # item B001
    RegisterPatron(uow).execute(
        "C002", PatronCategory.general, expires_on=date(2026, 6, 20)
    )  # clock is 2026-06-26 -> expired
    with pytest.raises(PatronExpired):
        CheckOut(uow, policy, clock).execute(s.item_barcode, "C002")


def test_suspend_blocks_then_reinstate_allows(uow, policy, clock):
    s = seed(uow)

    suspended = SuspendPatron(uow).execute(s.patron_card)
    assert suspended.status == "suspended"
    with pytest.raises(PatronSuspended):
        CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)

    reinstated = ReinstatePatron(uow).execute(s.patron_card)
    assert reinstated.status == "active"
    loan = CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)
    assert loan.item_barcode == s.item_barcode


def test_suspended_patron_cannot_renew(uow, policy, clock):
    s = seed(uow)
    CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)
    SuspendPatron(uow).execute(s.patron_card)
    with pytest.raises(PatronSuspended):
        RenewLoan(uow, policy, clock).execute(s.item_barcode)


def test_suspended_patron_cannot_place_hold(uow, policy, clock):
    s = seed(uow)
    SuspendPatron(uow).execute(s.patron_card)
    with pytest.raises(PatronSuspended):
        PlaceHold(uow, clock).execute(s.manifestation_id, s.patron_card)


def test_card_valid_through_its_expiry_day(uow, policy, clock):
    s = seed(uow)
    # clock is 2026-06-26; a card expiring *today* is still good today.
    RegisterPatron(uow).execute(
        "C002", PatronCategory.general, expires_on=date(2026, 6, 26)
    )
    loan = CheckOut(uow, policy, clock).execute(s.item_barcode, "C002")
    assert loan.patron_card == "C002"
