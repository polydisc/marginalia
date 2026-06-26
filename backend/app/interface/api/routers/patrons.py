from __future__ import annotations

from fastapi import APIRouter, Depends

from app.application.use_cases.patrons import (
    RegisterPatron,
    ReinstatePatron,
    SuspendPatron,
    UpdatePatron,
)
from app.domain.errors import PatronNotFound
from app.interface.api import deps
from app.interface.api.params import CodePath
from app.interface.api.schemas import (
    LoanLineResponse,
    PatronHoldResponse,
    PatronResponse,
    RegisterPatronRequest,
    UpdatePatronRequest,
)

router = APIRouter(tags=["patrons"])


def _require_patron(card_number: str, query) -> object:
    # Nested patron read endpoints should not let a mistyped or stale card look
    # like a real patron with no activity; fail fast with the same 404 as /patrons.
    patron = query.patron(card_number)
    if patron is None:
        raise PatronNotFound(f"patron {card_number} does not exist")
    return patron


@router.get("/patrons/{card_number}", response_model=PatronResponse)
def get_patron(card_number: CodePath, query=Depends(deps.get_query_service)):
    return _require_patron(card_number, query)


@router.get(
    "/patrons/{card_number}/loans", response_model=list[LoanLineResponse]
)
def patron_loans(
    card_number: CodePath, query=Depends(deps.get_query_service)
) -> list:
    _require_patron(card_number, query)
    return list(query.patron_loans(card_number))


@router.get(
    "/patrons/{card_number}/holds", response_model=list[PatronHoldResponse]
)
def patron_holds(
    card_number: CodePath, query=Depends(deps.get_query_service)
) -> list:
    _require_patron(card_number, query)
    return list(query.patron_holds(card_number))


@router.post("/patrons", status_code=201, response_model=PatronResponse)
def register_patron(
    body: RegisterPatronRequest,
    uc: RegisterPatron = Depends(deps.get_register_patron),
) -> PatronResponse:
    return uc.execute(body.card_number, body.category, body.expires_on)


@router.put("/patrons/{card_number}", response_model=PatronResponse)
def update_patron(
    card_number: CodePath,
    body: UpdatePatronRequest,
    uc: UpdatePatron = Depends(deps.get_update_patron),
) -> PatronResponse:
    return uc.execute(card_number, body.category, body.expires_on)


@router.post("/patrons/{card_number}/suspend", response_model=PatronResponse)
def suspend_patron(
    card_number: CodePath, uc: SuspendPatron = Depends(deps.get_suspend_patron)
) -> PatronResponse:
    return uc.execute(card_number)


@router.post("/patrons/{card_number}/reinstate", response_model=PatronResponse)
def reinstate_patron(
    card_number: CodePath,
    uc: ReinstatePatron = Depends(deps.get_reinstate_patron),
) -> PatronResponse:
    return uc.execute(card_number)
