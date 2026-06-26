"""Shared fixtures: an in-memory SQLite DB, a fixed clock, and seed helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.application.use_cases.catalog import (
    AddItem,
    CatalogManifestation,
    CreateWork,
)
from app.application.use_cases.patrons import RegisterPatron
from app.domain.value_objects import MaterialType, PatronCategory
from app.infrastructure.db import models  # noqa: F401  (register tables)
from app.infrastructure.db.base import Base
from app.infrastructure.db.engine import make_session_factory
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.policy_provider import StaticLoanPolicyProvider

FIXED_TODAY = date(2026, 6, 26)


class FixedClock:
    """Deterministic Clock adapter for tests."""

    def __init__(self, today: date = FIXED_TODAY) -> None:
        self._today = today

    def now(self) -> datetime:
        return datetime(self._today.year, self._today.month, self._today.day, 12)

    def today(self) -> date:
        return self._today


@pytest.fixture
def session_factory():
    # One shared in-memory database for the whole test (StaticPool keeps the
    # single connection alive so every session sees the same schema/data).
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def uow(session_factory):
    return SqlAlchemyUnitOfWork(session_factory)


@pytest.fixture
def policy():
    return StaticLoanPolicyProvider()


@pytest.fixture
def clock():
    return FixedClock()


@dataclass
class Seeded:
    work_id: int
    manifestation_id: int
    item_barcode: str
    patron_card: str


def seed(
    uow,
    *,
    material: MaterialType = MaterialType.book,
    category: PatronCategory = PatronCategory.general,
    barcode: str = "B001",
    card: str = "C001",
) -> Seeded:
    """Catalog one work/manifestation/item and register one patron."""
    work = CreateWork(uow).execute("Kokoro", "Soseki")
    man = CatalogManifestation(uow).execute(
        work_id=work.id, title="Kokoro", material_type=material
    )
    AddItem(uow).execute(man.id, barcode)
    RegisterPatron(uow).execute(card, category)
    return Seeded(
        work_id=work.id,
        manifestation_id=man.id,
        item_barcode=barcode,
        patron_card=card,
    )
