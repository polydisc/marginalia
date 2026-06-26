from __future__ import annotations

from datetime import date

from app.domain.value_objects import MaterialType, PatronCategory
from app.infrastructure.policy_provider import StaticLoanPolicyProvider


def test_general_book_policy_due_date():
    provider = StaticLoanPolicyProvider()
    policy = provider.policy_for(PatronCategory.general, MaterialType.book)
    assert policy.not_for_loan is False
    assert policy.due_date_from(date(2026, 6, 26)) == date(2026, 7, 10)


def test_reference_is_never_for_loan_regardless_of_category():
    provider = StaticLoanPolicyProvider()
    for category in PatronCategory:
        policy = provider.policy_for(category, MaterialType.reference)
        assert policy.not_for_loan is True


def test_categories_have_distinct_periods():
    provider = StaticLoanPolicyProvider()
    general = provider.policy_for(PatronCategory.general, MaterialType.book)
    student = provider.policy_for(PatronCategory.student, MaterialType.book)
    assert general.loan_period_days != student.loan_period_days
