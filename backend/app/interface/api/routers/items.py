from __future__ import annotations

from fastapi import APIRouter, Depends

from app.application.use_cases.catalog import ChangeItemState, GetItemAvailability
from app.interface.api import deps
from app.interface.api.params import CodePath
from app.interface.api.schemas import (
    ChangeItemStateRequest,
    ItemAvailabilityResponse,
    ItemResponse,
)

router = APIRouter(tags=["items"])


@router.get("/items/{barcode}", response_model=ItemAvailabilityResponse)
def get_item(
    barcode: CodePath,
    uc: GetItemAvailability = Depends(deps.get_item_availability),
) -> ItemAvailabilityResponse:
    return uc.execute(barcode)


@router.post("/items/{barcode}/state", response_model=ItemResponse)
def change_item_state(
    barcode: CodePath,
    body: ChangeItemStateRequest,
    uc: ChangeItemState = Depends(deps.get_change_item_state),
) -> ItemResponse:
    return uc.execute(barcode, body.state)
