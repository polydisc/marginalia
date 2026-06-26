"""Static loan-policy matrix (the values behind the domain ``LoanPolicy``).

Keyed by (patron category x material type). Reference material is not-for-loan.
In a fuller system these rows would live in storage and be editable by staff.
"""

from __future__ import annotations

from app.domain.policy import LoanPolicy, LoanPolicyProvider
from app.domain.value_objects import MaterialType, PatronCategory

# (category, material) -> policy
_MATRIX: dict[tuple[PatronCategory, MaterialType], LoanPolicy] = {
    (PatronCategory.general, MaterialType.book): LoanPolicy(
        loan_period_days=14, renewal_limit=2, max_concurrent_loans=10
    ),
    (PatronCategory.general, MaterialType.audiovisual): LoanPolicy(
        loan_period_days=7, renewal_limit=1, max_concurrent_loans=5
    ),
    (PatronCategory.student, MaterialType.book): LoanPolicy(
        loan_period_days=28, renewal_limit=3, max_concurrent_loans=20
    ),
    (PatronCategory.student, MaterialType.audiovisual): LoanPolicy(
        loan_period_days=7, renewal_limit=1, max_concurrent_loans=5
    ),
    (PatronCategory.child, MaterialType.book): LoanPolicy(
        loan_period_days=21, renewal_limit=2, max_concurrent_loans=5
    ),
    (PatronCategory.child, MaterialType.audiovisual): LoanPolicy(
        loan_period_days=7, renewal_limit=0, max_concurrent_loans=2
    ),
}

# Reference works are never lent, regardless of patron category.
_NOT_FOR_LOAN = LoanPolicy(
    loan_period_days=0,
    renewal_limit=0,
    max_concurrent_loans=0,
    not_for_loan=True,
)

_DEFAULT = LoanPolicy(
    loan_period_days=14, renewal_limit=1, max_concurrent_loans=5
)


class StaticLoanPolicyProvider(LoanPolicyProvider):
    def policy_for(
        self, category: PatronCategory, material: MaterialType
    ) -> LoanPolicy:
        if material is MaterialType.reference:
            return _NOT_FOR_LOAN
        return _MATRIX.get((category, material), _DEFAULT)
