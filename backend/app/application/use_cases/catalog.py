"""Cataloguing use cases: build the Work -> Manifestation -> Item spine."""

from __future__ import annotations

from app.application.dto import (
    ItemAvailabilityResult,
    ItemResult,
    ManifestationResult,
    WorkResult,
)
from app.application.unit_of_work import UnitOfWork
from app.domain.entities import Item, Manifestation, Work
from app.domain.errors import (
    DuplicateBarcode,
    ItemNotAvailable,
    ItemNotFound,
    ManifestationNotFound,
    WorkNotFound,
)
from app.domain.services import AvailabilityService
from app.domain.value_objects import ItemState, MaterialType


class CreateWork:
    """Create a Work: the abstract title at the head of the spine."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, title: str, author: str) -> WorkResult:
        with self._uow as uow:
            work = uow.works.add(Work(title=title, author=author))
            uow.commit()
            return WorkResult(id=work.id, title=work.title, author=work.author)


class CatalogManifestation:
    """Catalogue a Manifestation: a concrete edition of a Work."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        work_id: int,
        title: str,
        material_type: MaterialType,
        isbn: str | None = None,
        publisher: str | None = None,
    ) -> ManifestationResult:
        with self._uow as uow:
            if uow.works.get(work_id) is None:
                raise WorkNotFound(f"work {work_id} does not exist")
            m = uow.manifestations.add(
                Manifestation(
                    work_id=work_id,
                    title=title,
                    material_type=material_type,
                    isbn=isbn,
                    publisher=publisher,
                )
            )
            uow.commit()
            return ManifestationResult(
                id=m.id,
                work_id=m.work_id,
                title=m.title,
                material_type=m.material_type.value,
                isbn=m.isbn,
                publisher=m.publisher,
            )


class AddItem:
    """Add an Item: a physical, barcoded copy of a Manifestation."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, manifestation_id: int, barcode: str) -> ItemResult:
        with self._uow as uow:
            if uow.manifestations.get(manifestation_id) is None:
                raise ManifestationNotFound(
                    f"manifestation {manifestation_id} does not exist"
                )
            if uow.items.get_by_barcode(barcode) is not None:
                raise DuplicateBarcode(f"barcode {barcode} already exists")
            item = uow.items.add(
                Item(manifestation_id=manifestation_id, barcode=barcode)
            )
            uow.commit()
            return ItemResult(
                id=item.id,
                manifestation_id=item.manifestation_id,
                barcode=item.barcode,
                state=item.state.value,
            )


class UpdateWork:
    """Edit a Work's bibliographic fields (title, author)."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, work_id: int, title: str, author: str) -> WorkResult:
        with self._uow as uow:
            work = uow.works.get(work_id)
            if work is None:
                raise WorkNotFound(f"work {work_id} does not exist")
            work.title = title
            work.author = author
            uow.works.update(work)
            uow.commit()
            return WorkResult(id=work.id, title=work.title, author=work.author)


class UpdateManifestation:
    """Edit a manifestation's bibliographic fields.

    v1 allows changing material_type even to a not-for-loan kind (reference)
    while copies are on loan: those copies can still be returned, but cannot be
    renewed until then. Accepted as a transient, self-healing state.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        manifestation_id: int,
        title: str,
        material_type: MaterialType,
        isbn: str | None = None,
        publisher: str | None = None,
    ) -> ManifestationResult:
        with self._uow as uow:
            m = uow.manifestations.get(manifestation_id)
            if m is None:
                raise ManifestationNotFound(
                    f"manifestation {manifestation_id} does not exist"
                )
            m.title = title
            m.material_type = material_type
            m.isbn = isbn
            m.publisher = publisher
            uow.manifestations.update(m)
            uow.commit()
            return ManifestationResult(
                id=m.id,
                work_id=m.work_id,
                title=m.title,
                material_type=m.material_type.value,
                isbn=m.isbn,
                publisher=m.publisher,
            )


class ChangeItemState:
    """Move an Item's intrinsic state (mark lost / in-repair / withdraw / shelve).

    Taking a copy out of circulation requires it to be idle: not on an open loan
    and not set aside for a ready hold (return / re-assign it first).

    v1 decisions (deliberate):
    - A copy lost *while on loan* is handled as return-then-mark-lost, so an
      open loan and an intrinsic ``lost`` never coexist (keeps availability
      derivation unambiguous).
    - Withdrawing the last available copy of a Manifestation that still has
      pending holds can strand those holds (no copy left to fulfil them). Out of
      scope to auto-resolve in v1 — see the design doc's known limitations.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, barcode: str, target: ItemState) -> ItemResult:
        with self._uow as uow:
            item = uow.items.get_by_barcode(barcode)
            if item is None:
                raise ItemNotFound(f"item {barcode} does not exist")
            if target in (
                ItemState.in_repair,
                ItemState.lost,
                ItemState.withdrawn,
            ):
                if uow.loans.get_open_by_item(item.id) is not None:
                    raise ItemNotAvailable(
                        f"item {barcode} is on loan; return it first"
                    )
                if uow.holds.get_ready_for_item(item.id) is not None:
                    raise ItemNotAvailable(
                        f"item {barcode} is set aside for a hold"
                    )
            item.change_state(target)
            uow.items.update(item)
            uow.commit()
            return ItemResult(
                id=item.id,
                manifestation_id=item.manifestation_id,
                barcode=item.barcode,
                state=item.state.value,
            )


class GetItemAvailability:
    """Read model: an Item plus its *derived* availability (CONTEXT.md)."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._availability = AvailabilityService()

    def execute(self, barcode: str) -> ItemAvailabilityResult:
        with self._uow as uow:
            item = uow.items.get_by_barcode(barcode)
            if item is None:
                raise ItemNotFound(f"item {barcode} does not exist")
            open_loan = uow.loans.get_open_by_item(item.id)
            ready_hold = uow.holds.get_ready_for_item(item.id)
            availability = self._availability.availability_of(
                item, open_loan, ready_hold
            )
            return ItemAvailabilityResult(
                barcode=item.barcode,
                intrinsic_state=item.state.value,
                availability=availability.value,
            )
