"""Domain errors.

These are raised by entities/services/use cases and translated to HTTP status
codes at the interface boundary (never the other way round — the domain knows
nothing about HTTP).
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain rule violations."""


class NotFoundError(DomainError):
    """A referenced entity does not exist."""


class WorkNotFound(NotFoundError):
    pass


class ManifestationNotFound(NotFoundError):
    pass


class ItemNotFound(NotFoundError):
    pass


class PatronNotFound(NotFoundError):
    pass


class LoanNotOpen(DomainError):
    """No open loan exists for the item, or the loan is already closed."""


class ItemNotAvailable(DomainError):
    """The item cannot be lent right now (wrong state, on loan, or held)."""


class InvalidItemTransition(DomainError):
    """An item intrinsic-state change that the transition rules disallow."""


class NotForLoan(DomainError):
    """Policy forbids lending this (category x material) combination."""


class PatronCannotBorrow(DomainError):
    """The patron is blocked (overdue items, or at the concurrent-loan limit)."""


class PatronSuspended(PatronCannotBorrow):
    """The patron's account is suspended."""


class PatronExpired(PatronCannotBorrow):
    """The patron's card has expired."""


class RenewalLimitReached(DomainError):
    """The loan has been renewed the maximum number of times."""


class RenewalBlockedByHold(DomainError):
    """A renewal is refused because another patron is waiting (pending hold)."""


class HoldNotPending(DomainError):
    """A hold transition was attempted from a non-pending state."""


class HoldNotReady(DomainError):
    """A hold transition (fulfil / expire) was attempted on a non-ready hold."""


class HoldNotOpen(DomainError):
    """A cancel was attempted on a hold that is not open (pending/ready)."""


class HoldNotFound(NotFoundError):
    """The referenced hold does not exist."""


class DuplicateHold(DomainError):
    """The patron already has an open hold for this manifestation."""


class DuplicateBarcode(DomainError):
    pass


class DuplicateCardNumber(DomainError):
    pass
