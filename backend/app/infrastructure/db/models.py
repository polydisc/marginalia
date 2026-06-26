"""SQLAlchemy ORM models.

Kept strictly separate from the domain entities (ADR 0001): these never leak
past the repository — mappers convert to/from plain domain objects.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class WorkModel(Base):
    __tablename__ = "works"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    author: Mapped[str]


class ManifestationModel(Base):
    __tablename__ = "manifestations"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("works.id"), index=True)
    title: Mapped[str]
    material_type: Mapped[str]
    isbn: Mapped[str | None]
    publisher: Mapped[str | None]


class ItemModel(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    manifestation_id: Mapped[int] = mapped_column(
        ForeignKey("manifestations.id"), index=True
    )
    barcode: Mapped[str] = mapped_column(unique=True, index=True)
    state: Mapped[str]


class PatronModel(Base):
    __tablename__ = "patrons"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_number: Mapped[str] = mapped_column(unique=True, index=True)
    category: Mapped[str]
    # server_default keeps Alembic/manual upgrades safe for existing rows.
    status: Mapped[str] = mapped_column(server_default=text("'active'"))
    expires_on: Mapped[date | None]


class LoanModel(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    patron_id: Mapped[int] = mapped_column(ForeignKey("patrons.id"), index=True)
    loaned_at: Mapped[datetime]
    due_date: Mapped[date]
    returned_at: Mapped[datetime | None]
    renewal_count: Mapped[int] = mapped_column(default=0)

    # ADR 0003: at most one *open* loan per item — the concurrency backstop for
    # the no-double-loan invariant. A partial unique index on open rows only.
    __table_args__ = (
        Index(
            "uq_open_loan_per_item",
            "item_id",
            unique=True,
            sqlite_where=text("returned_at IS NULL"),
            postgresql_where=text("returned_at IS NULL"),
        ),
    )


class HoldModel(Base):
    __tablename__ = "holds"

    id: Mapped[int] = mapped_column(primary_key=True)
    manifestation_id: Mapped[int] = mapped_column(
        ForeignKey("manifestations.id"), index=True
    )
    patron_id: Mapped[int] = mapped_column(ForeignKey("patrons.id"), index=True)
    placed_at: Mapped[datetime]
    queue_position: Mapped[int]
    status: Mapped[str]
    assigned_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("items.id"), index=True
    )
    pickup_by: Mapped[date | None]

    # A patron should not occupy multiple queue slots for the same edition.
    # The use case checks this for clear errors; this partial unique index is
    # the concurrency backstop for pending/ready holds only.
    __table_args__ = (
        Index(
            "uq_open_hold_per_patron_manifestation",
            "manifestation_id",
            "patron_id",
            unique=True,
            sqlite_where=text("status IN ('pending', 'ready')"),
            postgresql_where=text("status IN ('pending', 'ready')"),
        ),
    )
