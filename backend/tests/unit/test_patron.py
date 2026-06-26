from __future__ import annotations

from datetime import date, datetime

import pytest

from app.domain.entities import Loan, Patron
from app.domain.errors import (
    PatronCannotBorrow,
    PatronExpired,
    PatronSuspended,
)
from app.domain.value_objects import PatronCategory, PatronStatus

TODAY = date(2026, 6, 26)


def _open_loan(due: date) -> Loan:
    return Loan(
        item_id=1, patron_id=1, loaned_at=datetime(2026, 6, 1, 12), due_date=due
    )


def _patron() -> Patron:
    return Patron(card_number="C001", category=PatronCategory.general)


def test_patron_with_no_loans_can_borrow():
    _patron().ensure_can_borrow([], max_concurrent_loans=5, today=TODAY)


def test_overdue_loan_blocks_borrowing():
    overdue = _open_loan(due=date(2026, 6, 20))
    with pytest.raises(PatronCannotBorrow):
        _patron().ensure_can_borrow([overdue], 5, TODAY)


def test_at_concurrent_limit_blocks_borrowing():
    loans = [_open_loan(due=date(2026, 7, 30)) for _ in range(3)]
    with pytest.raises(PatronCannotBorrow):
        _patron().ensure_can_borrow(loans, max_concurrent_loans=3, today=TODAY)


def test_suspended_patron_cannot_borrow():
    patron = _patron()
    patron.suspend()
    assert patron.status is PatronStatus.suspended
    with pytest.raises(PatronSuspended):
        patron.ensure_can_borrow([], 5, TODAY)


def test_reinstate_restores_borrowing():
    patron = _patron()
    patron.suspend()
    patron.reinstate()
    assert patron.status is PatronStatus.active
    patron.ensure_can_borrow([], 5, TODAY)  # no raise


def test_expired_card_blocks_borrowing():
    patron = Patron(
        card_number="C001",
        category=PatronCategory.general,
        expires_on=date(2026, 6, 25),  # yesterday
    )
    assert patron.is_expired(TODAY)
    with pytest.raises(PatronExpired):
        patron.ensure_can_borrow([], 5, TODAY)


def test_expiry_day_is_still_valid():
    patron = Patron(
        card_number="C001",
        category=PatronCategory.general,
        expires_on=TODAY,  # last valid day
    )
    assert not patron.is_expired(TODAY)
    patron.ensure_can_borrow([], 5, TODAY)  # no raise
