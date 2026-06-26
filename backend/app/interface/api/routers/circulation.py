from __future__ import annotations

from fastapi import APIRouter, Depends

from app.application.use_cases.circulation import (
    CancelHold,
    CheckIn,
    CheckOut,
    ExpireReadyHolds,
    PlaceHold,
    RenewLoan,
)
from app.interface.api import deps
from app.interface.api.params import CodePath, IdPath
from app.interface.api.schemas import (
    CancelHoldResponse,
    CheckInResponse,
    CheckOutRequest,
    ExpireHoldsResponse,
    HoldResponse,
    LoanResponse,
    PlaceHoldRequest,
    ReadyHoldResponse,
)

router = APIRouter(tags=["circulation"])


@router.get("/holds/ready", response_model=list[ReadyHoldResponse])
def ready_holds(query=Depends(deps.get_query_service)) -> list:
    return list(query.ready_holds())


@router.post("/loans", status_code=201, response_model=LoanResponse)
def check_out(
    body: CheckOutRequest, uc: CheckOut = Depends(deps.get_check_out)
) -> LoanResponse:
    return uc.execute(body.item_barcode, body.patron_card)


@router.post("/loans/{item_barcode}/return", response_model=CheckInResponse)
def check_in(
    item_barcode: CodePath, uc: CheckIn = Depends(deps.get_check_in)
) -> CheckInResponse:
    return uc.execute(item_barcode)


@router.post("/loans/{item_barcode}/renew", response_model=LoanResponse)
def renew_loan(
    item_barcode: CodePath, uc: RenewLoan = Depends(deps.get_renew_loan)
) -> LoanResponse:
    return uc.execute(item_barcode)


@router.post("/holds", status_code=201, response_model=HoldResponse)
def place_hold(
    body: PlaceHoldRequest, uc: PlaceHold = Depends(deps.get_place_hold)
) -> HoldResponse:
    return uc.execute(body.manifestation_id, body.patron_card)


@router.post("/holds/expire", response_model=ExpireHoldsResponse)
def expire_holds(
    uc: ExpireReadyHolds = Depends(deps.get_expire_holds),
) -> ExpireHoldsResponse:
    """Maintenance sweep: expire ready holds past their pickup-by date."""
    return uc.execute()


@router.post("/holds/{hold_id}/cancel", response_model=CancelHoldResponse)
def cancel_hold(
    hold_id: IdPath, uc: CancelHold = Depends(deps.get_cancel_hold)
) -> CancelHoldResponse:
    return uc.execute(hold_id)
