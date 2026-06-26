"""Composition root: wire ports to adapters and build use cases per request.

FastAPI has no DI container, so the wiring is explicit (ADR 0001: Clean
Architecture as self-imposed discipline). Singletons (session factory, policy,
clock) live on ``app.state``; use cases are constructed per request.
"""

from __future__ import annotations

from fastapi import Depends, Request

from app.application.use_cases.catalog import (
    AddItem,
    CatalogManifestation,
    ChangeItemState,
    CreateWork,
    GetItemAvailability,
    UpdateManifestation,
    UpdateWork,
)
from app.application.use_cases.circulation import (
    CancelHold,
    CheckIn,
    CheckOut,
    ExpireReadyHolds,
    PlaceHold,
    RenewLoan,
)
from app.application.use_cases.patrons import (
    RegisterPatron,
    ReinstatePatron,
    SuspendPatron,
    UpdatePatron,
)
from app.domain.clock import Clock
from app.domain.policy import LoanPolicyProvider
from app.infrastructure.db.queries import SqlAlchemyQueryService
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def get_uow(request: Request) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(request.app.state.session_factory)


def get_policy(request: Request) -> LoanPolicyProvider:
    return request.app.state.policy_provider


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


def get_pickup_window_days(request: Request) -> int:
    return request.app.state.hold_pickup_window_days


def get_query_service(request: Request) -> SqlAlchemyQueryService:
    # Built per request from app.state so it always uses the live clock
    # (tests override app.state.clock to drive overdue in the read model).
    return SqlAlchemyQueryService(
        request.app.state.session_factory, request.app.state.clock
    )


# --- use case providers -----------------------------------------------------


def get_create_work(uow=Depends(get_uow)) -> CreateWork:
    return CreateWork(uow)


def get_catalog_manifestation(uow=Depends(get_uow)) -> CatalogManifestation:
    return CatalogManifestation(uow)


def get_add_item(uow=Depends(get_uow)) -> AddItem:
    return AddItem(uow)


def get_item_availability(uow=Depends(get_uow)) -> GetItemAvailability:
    return GetItemAvailability(uow)


def get_change_item_state(uow=Depends(get_uow)) -> ChangeItemState:
    return ChangeItemState(uow)


def get_update_work(uow=Depends(get_uow)) -> UpdateWork:
    return UpdateWork(uow)


def get_update_manifestation(uow=Depends(get_uow)) -> UpdateManifestation:
    return UpdateManifestation(uow)


def get_register_patron(uow=Depends(get_uow)) -> RegisterPatron:
    return RegisterPatron(uow)


def get_update_patron(uow=Depends(get_uow)) -> UpdatePatron:
    return UpdatePatron(uow)


def get_suspend_patron(uow=Depends(get_uow)) -> SuspendPatron:
    return SuspendPatron(uow)


def get_reinstate_patron(uow=Depends(get_uow)) -> ReinstatePatron:
    return ReinstatePatron(uow)


def get_check_out(
    uow=Depends(get_uow),
    policy=Depends(get_policy),
    clock=Depends(get_clock),
) -> CheckOut:
    return CheckOut(uow, policy, clock)


def get_check_in(
    uow=Depends(get_uow),
    clock=Depends(get_clock),
    pickup_window_days=Depends(get_pickup_window_days),
) -> CheckIn:
    return CheckIn(uow, clock, pickup_window_days)


def get_expire_holds(
    uow=Depends(get_uow),
    clock=Depends(get_clock),
    pickup_window_days=Depends(get_pickup_window_days),
) -> ExpireReadyHolds:
    return ExpireReadyHolds(uow, clock, pickup_window_days)


def get_cancel_hold(
    uow=Depends(get_uow),
    clock=Depends(get_clock),
    pickup_window_days=Depends(get_pickup_window_days),
) -> CancelHold:
    return CancelHold(uow, clock, pickup_window_days)


def get_renew_loan(
    uow=Depends(get_uow),
    policy=Depends(get_policy),
    clock=Depends(get_clock),
) -> RenewLoan:
    return RenewLoan(uow, policy, clock)


def get_place_hold(uow=Depends(get_uow), clock=Depends(get_clock)) -> PlaceHold:
    return PlaceHold(uow, clock)
