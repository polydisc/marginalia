"""Circulation use cases: check out, check in, renew, place hold.

These orchestrate the aggregates; the rules live in the entities/policy, and
the no-double-loan invariant is backstopped by a DB constraint (ADR 0003).
"""

from __future__ import annotations

from datetime import timedelta

from app.application.dto import (
    CancelHoldResult,
    CheckInResult,
    ExpireHoldsResult,
    HoldResult,
    LoanResult,
)
from app.application.unit_of_work import UnitOfWork
from app.domain.clock import Clock
from app.domain.entities import Hold, Loan
from app.domain.errors import (
    DuplicateHold,
    HoldNotFound,
    ItemNotAvailable,
    ItemNotFound,
    LoanNotOpen,
    ManifestationNotFound,
    NotForLoan,
    PatronNotFound,
    RenewalBlockedByHold,
)
from app.domain.policy import LoanPolicyProvider
from app.domain.value_objects import HoldStatus


class CheckOut:
    def __init__(
        self, uow: UnitOfWork, policy: LoanPolicyProvider, clock: Clock
    ) -> None:
        self._uow = uow
        self._policy = policy
        self._clock = clock

    def execute(self, item_barcode: str, patron_card: str) -> LoanResult:
        with self._uow as uow:
            item = uow.items.get_by_barcode(item_barcode)
            if item is None:
                raise ItemNotFound(f"item {item_barcode} does not exist")
            patron = uow.patrons.get_by_card_number(patron_card)
            if patron is None:
                raise PatronNotFound(f"patron {patron_card} does not exist")
            manifestation = uow.manifestations.get(item.manifestation_id)
            if manifestation is None:
                raise ManifestationNotFound(
                    f"manifestation {item.manifestation_id} does not exist"
                )

            policy = self._policy.policy_for(
                patron.category, manifestation.material_type
            )
            if policy.not_for_loan:
                raise NotForLoan(
                    f"{manifestation.material_type.value} is not for loan"
                )

            # Availability = intrinsic state + no open loan + not held for another.
            item.ensure_intrinsically_loanable()
            if uow.loans.get_open_by_item(item.id) is not None:
                raise ItemNotAvailable(f"item {item_barcode} is already on loan")
            ready_hold = uow.holds.get_ready_for_item(item.id)
            if ready_hold is not None and ready_hold.patron_id != patron.id:
                raise ItemNotAvailable(
                    f"item {item_barcode} is set aside for another patron"
                )

            # Patron eligibility (overdue / concurrent-loan limit).
            open_loans = uow.loans.list_open_by_patron(patron.id)
            patron.ensure_can_borrow(
                open_loans, policy.max_concurrent_loans, self._clock.today()
            )

            loan = uow.loans.add(
                Loan(
                    item_id=item.id,
                    patron_id=patron.id,
                    loaned_at=self._clock.now(),
                    due_date=policy.due_date_from(self._clock.today()),
                )
            )

            # If this patron was the one the item was set aside for, fulfill it.
            # ``ready_hold`` came from get_ready_for_item (status == ready), so
            # fulfill() cannot raise here; any failure rolls back the loan too.
            if ready_hold is not None and ready_hold.patron_id == patron.id:
                ready_hold.fulfill()
                uow.holds.update(ready_hold)

            uow.commit()
            return LoanResult(
                loan_id=loan.id,
                item_barcode=item.barcode,
                patron_card=patron.card_number,
                due_date=loan.due_date,
                renewal_count=loan.renewal_count,
            )


class CheckIn:
    def __init__(
        self, uow: UnitOfWork, clock: Clock, pickup_window_days: int
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._pickup_window_days = pickup_window_days

    def execute(self, item_barcode: str) -> CheckInResult:
        with self._uow as uow:
            item = uow.items.get_by_barcode(item_barcode)
            if item is None:
                raise ItemNotFound(f"item {item_barcode} does not exist")
            loan = uow.loans.get_open_by_item(item.id)
            if loan is None:
                raise LoanNotOpen(f"item {item_barcode} is not on loan")

            loan.close(self._clock.now())
            uow.loans.update(loan)

            # Fulfillment: hand the returned item to the head of the queue,
            # giving the waiting patron until `pickup_by` to collect it.
            hold_triggered = False
            ready_hold_id: int | None = None
            pending = uow.holds.list_pending_by_manifestation(
                item.manifestation_id
            )
            if pending:
                head = pending[0]
                pickup_by = self._clock.today() + timedelta(
                    days=self._pickup_window_days
                )
                head.assign_item(item.id, pickup_by)
                uow.holds.update(head)
                hold_triggered = True
                ready_hold_id = head.id

            uow.commit()
            return CheckInResult(
                item_barcode=item.barcode,
                hold_triggered=hold_triggered,
                ready_hold_id=ready_hold_id,
            )


class ExpireReadyHolds:
    """Sweep ready holds past their pickup-by date (a scheduled maintenance op).

    Each expired hold releases its copy; if another patron is waiting on the
    same manifestation, the copy is handed to the queue head with a fresh
    pickup window, otherwise it returns to the shelf (no ready hold -> the
    item's derived availability becomes `available` again).
    """

    def __init__(
        self, uow: UnitOfWork, clock: Clock, pickup_window_days: int
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._pickup_window_days = pickup_window_days

    def execute(self) -> ExpireHoldsResult:
        with self._uow as uow:
            today = self._clock.today()
            expired = uow.holds.list_ready_expired(today)
            reassigned = 0
            for hold in expired:
                item_id = hold.assigned_item_id
                hold.expire()
                uow.holds.update(hold)
                if item_id is None:
                    continue
                pending = uow.holds.list_pending_by_manifestation(
                    hold.manifestation_id
                )
                if pending:
                    head = pending[0]
                    head.assign_item(
                        item_id, today + timedelta(days=self._pickup_window_days)
                    )
                    uow.holds.update(head)
                    reassigned += 1
            uow.commit()
            return ExpireHoldsResult(
                expired=len(expired), reassigned=reassigned
            )


class RenewLoan:
    def __init__(
        self, uow: UnitOfWork, policy: LoanPolicyProvider, clock: Clock
    ) -> None:
        self._uow = uow
        self._policy = policy
        self._clock = clock

    def execute(self, item_barcode: str) -> LoanResult:
        with self._uow as uow:
            item = uow.items.get_by_barcode(item_barcode)
            if item is None:
                raise ItemNotFound(f"item {item_barcode} does not exist")
            loan = uow.loans.get_open_by_item(item.id)
            if loan is None:
                raise LoanNotOpen(f"item {item_barcode} is not on loan")
            manifestation = uow.manifestations.get(item.manifestation_id)
            if manifestation is None:
                raise ManifestationNotFound(
                    f"manifestation {item.manifestation_id} does not exist"
                )
            patron = uow.patrons.get(loan.patron_id)
            if patron is None:
                raise PatronNotFound(f"patron {loan.patron_id} does not exist")

            # A suspended/expired patron cannot renew either.
            patron.ensure_active(self._clock.today())

            # v1: a waiting patron (pending hold) blocks renewal.
            if uow.holds.list_pending_by_manifestation(manifestation.id):
                raise RenewalBlockedByHold(
                    f"item {item_barcode} has a pending hold; cannot renew"
                )

            policy = self._policy.policy_for(
                patron.category, manifestation.material_type
            )
            loan.renew(
                policy.renewal_limit,
                policy.due_date_from(self._clock.today()),
            )
            uow.loans.update(loan)
            uow.commit()
            return LoanResult(
                loan_id=loan.id,
                item_barcode=item.barcode,
                patron_card=patron.card_number,
                due_date=loan.due_date,
                renewal_count=loan.renewal_count,
            )


class CancelHold:
    """Cancel an open hold. If a ready hold is cancelled, its set-aside copy is
    handed to the next waiting hold (fresh pickup window) or released to the
    shelf — the same release logic as expiry."""

    def __init__(
        self, uow: UnitOfWork, clock: Clock, pickup_window_days: int
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._pickup_window_days = pickup_window_days

    def execute(self, hold_id: int) -> CancelHoldResult:
        with self._uow as uow:
            hold = uow.holds.get(hold_id)
            if hold is None:
                raise HoldNotFound(f"hold {hold_id} does not exist")
            item_id = (
                hold.assigned_item_id
                if hold.status is HoldStatus.ready
                else None
            )
            hold.cancel()
            uow.holds.update(hold)

            reassigned = 0
            if item_id is not None:
                pending = uow.holds.list_pending_by_manifestation(
                    hold.manifestation_id
                )
                if pending:
                    head = pending[0]
                    head.assign_item(
                        item_id,
                        self._clock.today()
                        + timedelta(days=self._pickup_window_days),
                    )
                    uow.holds.update(head)
                    reassigned = 1

            uow.commit()
            return CancelHoldResult(
                hold_id=hold_id, status=hold.status.value, reassigned=reassigned
            )


class PlaceHold:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def execute(self, manifestation_id: int, patron_card: str) -> HoldResult:
        with self._uow as uow:
            manifestation = uow.manifestations.get(manifestation_id)
            if manifestation is None:
                raise ManifestationNotFound(
                    f"manifestation {manifestation_id} does not exist"
                )
            patron = uow.patrons.get_by_card_number(patron_card)
            if patron is None:
                raise PatronNotFound(f"patron {patron_card} does not exist")
            # A hold is a future borrow, so a suspended/expired patron may not
            # queue for one either.
            patron.ensure_active(self._clock.today())
            if (
                uow.holds.get_open_by_patron_and_manifestation(
                    patron.id, manifestation_id
                )
                is not None
            ):
                raise DuplicateHold(
                    f"patron {patron_card} already has an open hold "
                    f"for manifestation {manifestation_id}"
                )

            position = uow.holds.next_queue_position(manifestation_id)
            hold = uow.holds.add(
                Hold(
                    manifestation_id=manifestation_id,
                    patron_id=patron.id,
                    placed_at=self._clock.now(),
                    queue_position=position,
                )
            )
            uow.commit()
            return HoldResult(
                hold_id=hold.id,
                manifestation_id=manifestation_id,
                patron_card=patron.card_number,
                queue_position=hold.queue_position,
                status=hold.status.value,
            )
