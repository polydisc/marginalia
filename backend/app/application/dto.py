"""Plain output DTOs returned by use cases.

Dataclasses, not Pydantic — the application layer stays framework-free. The
interface layer maps these to Pydantic response models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class WorkResult:
    id: int
    title: str
    author: str


@dataclass
class ManifestationResult:
    id: int
    work_id: int
    title: str
    material_type: str
    isbn: str | None
    publisher: str | None


@dataclass
class ItemResult:
    id: int
    manifestation_id: int
    barcode: str
    state: str


@dataclass
class PatronResult:
    id: int
    card_number: str
    category: str
    status: str
    expires_on: date | None


@dataclass
class LoanResult:
    loan_id: int
    item_barcode: str
    patron_card: str
    due_date: date
    renewal_count: int


@dataclass
class CheckInResult:
    item_barcode: str
    hold_triggered: bool
    ready_hold_id: int | None


@dataclass
class HoldResult:
    hold_id: int
    manifestation_id: int
    patron_card: str
    queue_position: int
    status: str


@dataclass
class ItemAvailabilityResult:
    barcode: str
    intrinsic_state: str
    availability: str


@dataclass
class ExpireHoldsResult:
    expired: int
    reassigned: int


@dataclass
class CancelHoldResult:
    hold_id: int
    status: str
    reassigned: int


# --- read models (projections for the UI) -----------------------------------


@dataclass
class CatalogItemView:
    barcode: str
    availability: str


@dataclass
class CatalogManifestationView:
    id: int
    title: str
    material_type: str
    isbn: str | None
    publisher: str | None
    items: list[CatalogItemView]


@dataclass
class CatalogWorkView:
    id: int
    title: str
    author: str
    manifestations: list[CatalogManifestationView]


@dataclass
class LoanLineView:
    item_barcode: str
    title: str
    author: str
    due_date: date
    renewal_count: int
    overdue: bool


@dataclass
class ReadyHoldView:
    hold_id: int
    title: str
    patron_card: str
    item_barcode: str | None
    queue_position: int


@dataclass
class PatronView:
    id: int
    card_number: str
    category: str
    status: str
    expires_on: date | None


@dataclass
class PatronHoldView:
    hold_id: int
    manifestation_id: int
    title: str
    status: str
    queue_position: int
    pickup_by: date | None
