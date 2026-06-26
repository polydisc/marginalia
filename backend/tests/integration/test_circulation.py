from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.application.use_cases.catalog import AddItem, GetItemAvailability
from app.application.use_cases.circulation import CheckIn, CheckOut, RenewLoan
from app.domain.errors import (
    ItemNotAvailable,
    LoanNotOpen,
    NotForLoan,
    PatronCannotBorrow,
    RenewalLimitReached,
)
from app.domain.value_objects import MaterialType
from tests.conftest import FIXED_TODAY, FixedClock, seed


def test_checkout_then_checkin_round_trip(uow, policy, clock):
    s = seed(uow)

    result = CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)
    assert result.due_date == date(2026, 7, 10)  # 2026-06-26 + 14 (general/book)
    assert (
        GetItemAvailability(uow).execute(s.item_barcode).availability
        == "on_loan"
    )

    CheckIn(uow, clock, 7).execute(s.item_barcode)
    assert (
        GetItemAvailability(uow).execute(s.item_barcode).availability
        == "available"
    )


def test_double_checkout_blocked_in_domain(uow, policy, clock):
    s = seed(uow)
    CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)
    with pytest.raises(ItemNotAvailable):
        CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)


def test_reference_material_is_not_for_loan(uow, policy, clock):
    s = seed(uow, material=MaterialType.reference)
    with pytest.raises(NotForLoan):
        CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)


def test_overdue_loan_blocks_further_borrowing(uow, policy):
    s = seed(uow)
    AddItem(uow).execute(s.manifestation_id, "B002")

    # Borrow B001 "today"; due in 14 days.
    CheckOut(uow, policy, FixedClock(FIXED_TODAY)).execute("B001", s.patron_card)

    # 30 days later B001 is overdue -> cannot take out B002.
    late = FixedClock(date(2026, 7, 26))
    with pytest.raises(PatronCannotBorrow):
        CheckOut(uow, policy, late).execute("B002", s.patron_card)


def test_renew_until_limit_then_blocked(uow, policy, clock):
    s = seed(uow)  # general/book -> renewal_limit = 2
    CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)

    r1 = RenewLoan(uow, policy, clock).execute(s.item_barcode)
    assert r1.renewal_count == 1
    r2 = RenewLoan(uow, policy, clock).execute(s.item_barcode)
    assert r2.renewal_count == 2
    with pytest.raises(RenewalLimitReached):
        RenewLoan(uow, policy, clock).execute(s.item_barcode)


def test_checkin_with_no_open_loan_raises(uow, clock):
    s = seed(uow)
    with pytest.raises(LoanNotOpen):
        CheckIn(uow, clock, 7).execute(s.item_barcode)


def test_partial_unique_index_is_the_concurrency_backstop(session_factory):
    """ADR 0003: the DB rejects a second *open* loan even bypassing the domain,
    but allows a new loan once the previous one is returned."""
    from app.infrastructure.db.models import LoanModel

    session = session_factory()
    session.add(
        LoanModel(
            item_id=1,
            patron_id=1,
            loaned_at=datetime(2026, 6, 26, 12),
            due_date=date(2026, 7, 10),
        )
    )
    session.commit()

    # Second open loan for the same item -> rejected by the partial unique index.
    session.add(
        LoanModel(
            item_id=1,
            patron_id=2,
            loaned_at=datetime(2026, 6, 26, 12),
            due_date=date(2026, 7, 10),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    # Close the first, then a new open loan is allowed (index only covers open).
    session = session_factory()
    first = session.get(LoanModel, 1)
    first.returned_at = datetime(2026, 6, 30, 12)
    session.commit()
    session.add(
        LoanModel(
            item_id=1,
            patron_id=2,
            loaned_at=datetime(2026, 7, 1, 12),
            due_date=date(2026, 7, 15),
        )
    )
    session.commit()  # no error
