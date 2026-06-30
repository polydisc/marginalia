from __future__ import annotations

from datetime import date, datetime

from app.adapter.db.models import HoldModel
from app.tasks import run_expire_holds


def test_run_expire_holds_expires_past_pickup(session_factory):
    # A ready hold whose pickup-by is long past (well before any real "today").
    with session_factory() as session:
        session.add(
            HoldModel(
                manifestation_id=1,
                patron_id=1,
                placed_at=datetime(2000, 1, 1, 12),
                queue_position=1,
                status="ready",
                assigned_item_id=1,
                pickup_by=date(2000, 1, 8),
            )
        )
        session.commit()

    result = run_expire_holds(session_factory)
    assert result.expired == 1
    assert result.reassigned == 0
    with session_factory() as session:
        assert session.get(HoldModel, 1).status == "expired"


def test_run_expire_holds_noop_when_nothing_due(session_factory):
    result = run_expire_holds(session_factory)
    assert result.expired == 0
