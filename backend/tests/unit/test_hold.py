from __future__ import annotations

from datetime import date, datetime

import pytest

from app.domain.entities import Hold
from app.domain.errors import HoldNotPending, HoldNotReady
from app.domain.value_objects import HoldStatus


def _pending() -> Hold:
    return Hold(
        manifestation_id=1,
        patron_id=1,
        placed_at=datetime(2026, 6, 26, 12),
        queue_position=1,
    )


def test_assign_item_makes_ready_with_pickup_by():
    hold = _pending()
    hold.assign_item(item_id=7, pickup_by=date(2026, 7, 3))
    assert hold.status is HoldStatus.ready
    assert hold.assigned_item_id == 7
    assert hold.pickup_by == date(2026, 7, 3)


def test_cannot_assign_a_non_pending_hold():
    hold = _pending()
    hold.assign_item(7, date(2026, 7, 3))
    with pytest.raises(HoldNotPending):
        hold.assign_item(8, date(2026, 7, 4))


def test_expire_only_from_ready():
    hold = _pending()
    with pytest.raises(HoldNotReady):
        hold.expire()
    hold.assign_item(7, date(2026, 7, 3))
    hold.expire()
    assert hold.status is HoldStatus.expired


def test_fulfill_requires_ready():
    hold = _pending()
    with pytest.raises(HoldNotReady):
        hold.fulfill()
