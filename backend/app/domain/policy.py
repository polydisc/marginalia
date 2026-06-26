"""Loan policy — a domain concept whose *values* are injected from outside.

The rules (how a due date is computed, what the limits are) live in the domain;
the numbers come from a ``LoanPolicyProvider`` adapter (config/storage), never
hard-coded in entities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol

from app.domain.value_objects import MaterialType, PatronCategory


@dataclass(frozen=True)
class LoanPolicy:
    """Rules for one (patron category x material type) pair."""

    loan_period_days: int
    renewal_limit: int
    max_concurrent_loans: int
    not_for_loan: bool = False

    def due_date_from(self, loaned_on: date) -> date:
        return loaned_on + timedelta(days=self.loan_period_days)


class LoanPolicyProvider(Protocol):
    """Port: supplies the policy for a given (category, material) pair."""

    def policy_for(
        self, category: PatronCategory, material: MaterialType
    ) -> LoanPolicy: ...
