"""SQLAlchemy read-model queries (the QueryService adapter).

Each opens its own short-lived session and returns plain view DTOs. These are
read projections, so they join across what are separate write aggregates.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto import (
    CatalogItemView,
    CatalogManifestationView,
    CatalogWorkView,
    LoanLineView,
    PatronHoldView,
    PatronView,
    ReadyHoldView,
)
from app.domain.clock import Clock
from app.infrastructure.db.models import (
    HoldModel,
    ItemModel,
    LoanModel,
    ManifestationModel,
    PatronModel,
    WorkModel,
)


def _derive_availability(
    state: str, has_open_loan: bool, has_ready_hold: bool
) -> str:
    if state in ("in_repair", "lost", "withdrawn"):
        return state
    if has_open_loan:
        return "on_loan"
    if has_ready_hold:
        return "on_hold_shelf"
    return "available"


class SqlAlchemyQueryService:
    def __init__(
        self, session_factory: sessionmaker[Session], clock: Clock
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock

    def catalog(self) -> Sequence[CatalogWorkView]:
        with self._session_factory() as session:
            works = session.scalars(
                select(WorkModel).order_by(WorkModel.title)
            ).all()
            manifs = session.scalars(select(ManifestationModel)).all()
            items = session.scalars(select(ItemModel)).all()
            # Derived sets — two cheap queries instead of per-item lookups.
            on_loan = set(
                session.scalars(
                    select(LoanModel.item_id).where(
                        LoanModel.returned_at.is_(None)
                    )
                ).all()
            )
            on_hold = set(
                session.scalars(
                    select(HoldModel.assigned_item_id).where(
                        HoldModel.status == "ready",
                        HoldModel.assigned_item_id.is_not(None),
                    )
                ).all()
            )

            items_by_manif: dict[int, list[CatalogItemView]] = {}
            for it in items:
                items_by_manif.setdefault(it.manifestation_id, []).append(
                    CatalogItemView(
                        barcode=it.barcode,
                        availability=_derive_availability(
                            it.state, it.id in on_loan, it.id in on_hold
                        ),
                    )
                )

            manifs_by_work: dict[int, list[CatalogManifestationView]] = {}
            for m in manifs:
                manifs_by_work.setdefault(m.work_id, []).append(
                    CatalogManifestationView(
                        id=m.id,
                        title=m.title,
                        material_type=m.material_type,
                        isbn=m.isbn,
                        publisher=m.publisher,
                        items=items_by_manif.get(m.id, []),
                    )
                )

            return [
                CatalogWorkView(
                    id=w.id,
                    title=w.title,
                    author=w.author,
                    manifestations=manifs_by_work.get(w.id, []),
                )
                for w in works
            ]

    def patron(self, card_number: str) -> PatronView | None:
        with self._session_factory() as session:
            row = session.scalar(
                select(PatronModel).where(
                    PatronModel.card_number == card_number
                )
            )
            if row is None:
                return None
            return PatronView(
                id=row.id,
                card_number=row.card_number,
                category=row.category,
                status=row.status,
                expires_on=row.expires_on,
            )

    def patron_loans(self, card_number: str) -> Sequence[LoanLineView]:
        today = self._clock.today()
        with self._session_factory() as session:
            rows = session.execute(
                select(
                    ItemModel.barcode,
                    WorkModel.title,
                    WorkModel.author,
                    LoanModel.due_date,
                    LoanModel.renewal_count,
                )
                .join(PatronModel, PatronModel.id == LoanModel.patron_id)
                .join(ItemModel, ItemModel.id == LoanModel.item_id)
                .join(
                    ManifestationModel,
                    ManifestationModel.id == ItemModel.manifestation_id,
                )
                .join(WorkModel, WorkModel.id == ManifestationModel.work_id)
                .where(
                    PatronModel.card_number == card_number,
                    LoanModel.returned_at.is_(None),
                )
                .order_by(LoanModel.due_date)
            ).all()
            return [
                LoanLineView(
                    item_barcode=barcode,
                    title=title,
                    author=author,
                    due_date=due_date,
                    renewal_count=renewal_count,
                    overdue=due_date < today,
                )
                for (barcode, title, author, due_date, renewal_count) in rows
            ]

    def patron_holds(self, card_number: str) -> Sequence[PatronHoldView]:
        with self._session_factory() as session:
            rows = session.execute(
                select(
                    HoldModel.id,
                    HoldModel.manifestation_id,
                    WorkModel.title,
                    HoldModel.status,
                    HoldModel.queue_position,
                    HoldModel.pickup_by,
                )
                .join(
                    ManifestationModel,
                    ManifestationModel.id == HoldModel.manifestation_id,
                )
                .join(WorkModel, WorkModel.id == ManifestationModel.work_id)
                .join(PatronModel, PatronModel.id == HoldModel.patron_id)
                .where(
                    PatronModel.card_number == card_number,
                    HoldModel.status.in_(("pending", "ready")),
                )
                .order_by(HoldModel.id)
            ).all()
            return [
                PatronHoldView(
                    hold_id=hid,
                    manifestation_id=mid,
                    title=title,
                    status=status,
                    queue_position=qpos,
                    pickup_by=pickup_by,
                )
                for (hid, mid, title, status, qpos, pickup_by) in rows
            ]

    def ready_holds(self) -> Sequence[ReadyHoldView]:
        with self._session_factory() as session:
            rows = session.execute(
                select(
                    HoldModel.id,
                    WorkModel.title,
                    PatronModel.card_number,
                    ItemModel.barcode,
                    HoldModel.queue_position,
                )
                .join(
                    ManifestationModel,
                    ManifestationModel.id == HoldModel.manifestation_id,
                )
                .join(WorkModel, WorkModel.id == ManifestationModel.work_id)
                .join(PatronModel, PatronModel.id == HoldModel.patron_id)
                .join(
                    ItemModel,
                    ItemModel.id == HoldModel.assigned_item_id,
                    isouter=True,
                )
                .where(HoldModel.status == "ready")
                .order_by(HoldModel.id)
            ).all()
            return [
                ReadyHoldView(
                    hold_id=hold_id,
                    title=title,
                    patron_card=card,
                    item_barcode=barcode,
                    queue_position=queue_position,
                )
                for (hold_id, title, card, barcode, queue_position) in rows
            ]
