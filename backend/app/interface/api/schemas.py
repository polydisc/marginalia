"""Pydantic request/response schemas — confined to the interface layer.

Responses are built from the application-layer DTOs via ``from_attributes``.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.value_objects import ItemState, MaterialType, PatronCategory
from app.interface.api.params import DB_ID_MAX

# Bound and trim request input at the boundary, so whitespace-only or unbounded
# strings never reach the domain/DB. Titles are prose; codes are intentionally
# short operational identifiers.
Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
OptText = (
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    ]
    | None
)
Code = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
]
Isbn = (
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=20),
    ]
    | None
)
# Same 64-bit surrogate-key bound as path ids (see params.DB_ID_MAX): keep an
# oversized JSON integer from overflowing the DB lookup into a 500.
RecordId = Annotated[int, Field(ge=1, le=DB_ID_MAX)]


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- requests ---------------------------------------------------------------


class CreateWorkRequest(BaseModel):
    title: Text
    author: Text


class CreateManifestationRequest(BaseModel):
    work_id: RecordId
    title: Text
    material_type: MaterialType
    isbn: Isbn = None
    publisher: OptText = None


class UpdateWorkRequest(BaseModel):
    title: Text
    author: Text


class UpdateManifestationRequest(BaseModel):
    title: Text
    material_type: MaterialType
    isbn: Isbn = None
    publisher: OptText = None


class UpdatePatronRequest(BaseModel):
    category: PatronCategory
    expires_on: date | None = None


class AddItemRequest(BaseModel):
    barcode: Code


class ChangeItemStateRequest(BaseModel):
    state: ItemState


class RegisterPatronRequest(BaseModel):
    card_number: Code
    category: PatronCategory
    expires_on: date | None = None


class CheckOutRequest(BaseModel):
    item_barcode: Code
    patron_card: Code


class PlaceHoldRequest(BaseModel):
    manifestation_id: RecordId
    patron_card: Code


# --- responses --------------------------------------------------------------


class WorkResponse(_Out):
    id: int
    title: str
    author: str


class ManifestationResponse(_Out):
    id: int
    work_id: int
    title: str
    material_type: str
    isbn: str | None
    publisher: str | None


class ItemResponse(_Out):
    id: int
    manifestation_id: int
    barcode: str
    state: str


class PatronResponse(_Out):
    id: int
    card_number: str
    category: str
    status: str
    expires_on: date | None


class LoanResponse(_Out):
    loan_id: int
    item_barcode: str
    patron_card: str
    due_date: date
    renewal_count: int


class CheckInResponse(_Out):
    item_barcode: str
    hold_triggered: bool
    ready_hold_id: int | None


class HoldResponse(_Out):
    hold_id: int
    manifestation_id: int
    patron_card: str
    queue_position: int
    status: str


class ItemAvailabilityResponse(_Out):
    barcode: str
    intrinsic_state: str
    availability: str


class ExpireHoldsResponse(_Out):
    expired: int
    reassigned: int


# --- read models ------------------------------------------------------------


class CatalogItemResponse(_Out):
    barcode: str
    availability: str


class CatalogManifestationResponse(_Out):
    id: int
    title: str
    material_type: str
    isbn: str | None
    publisher: str | None
    items: list[CatalogItemResponse]


class CatalogWorkResponse(_Out):
    id: int
    title: str
    author: str
    manifestations: list[CatalogManifestationResponse]


class LoanLineResponse(_Out):
    item_barcode: str
    title: str
    author: str
    due_date: date
    renewal_count: int
    overdue: bool


class ReadyHoldResponse(_Out):
    hold_id: int
    title: str
    patron_card: str
    item_barcode: str | None
    queue_position: int


class PatronHoldResponse(_Out):
    hold_id: int
    manifestation_id: int
    title: str
    status: str
    queue_position: int
    pickup_by: date | None


class CancelHoldResponse(_Out):
    hold_id: int
    status: str
    reassigned: int
