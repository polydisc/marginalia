from __future__ import annotations

from datetime import date, datetime

import pytest

from app.domain.entities import Loan
from app.domain.errors import LoanNotOpen, RenewalLimitReached


def _loan(due: date = date(2026, 6, 26)) -> Loan:
    return Loan(
        item_id=1,
        patron_id=1,
        loaned_at=datetime(2026, 6, 12, 12),
        due_date=due,
    )


def test_loan_is_open_until_returned():
    loan = _loan()
    assert loan.is_open
    loan.close(datetime(2026, 6, 20, 12))
    assert not loan.is_open


def test_is_overdue_only_while_open_and_past_due():
    loan = _loan(due=date(2026, 6, 20))
    assert loan.is_overdue(date(2026, 6, 21))
    assert not loan.is_overdue(date(2026, 6, 20))
    loan.close(datetime(2026, 6, 22, 12))
    assert not loan.is_overdue(date(2026, 6, 30))  # closed -> never overdue


def test_renew_increments_and_moves_due_date():
    loan = _loan()
    loan.renew(renewal_limit=2, new_due_date=date(2026, 7, 10))
    assert loan.renewal_count == 1
    assert loan.due_date == date(2026, 7, 10)


def test_renew_past_limit_raises():
    loan = _loan()
    loan.renew(2, date(2026, 7, 10))
    loan.renew(2, date(2026, 7, 24))
    with pytest.raises(RenewalLimitReached):
        loan.renew(2, date(2026, 8, 7))


def test_cannot_renew_or_close_a_returned_loan():
    loan = _loan()
    loan.close(datetime(2026, 6, 20, 12))
    with pytest.raises(LoanNotOpen):
        loan.renew(2, date(2026, 7, 10))
    with pytest.raises(LoanNotOpen):
        loan.close(datetime(2026, 6, 21, 12))
