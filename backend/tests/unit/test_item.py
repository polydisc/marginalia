from __future__ import annotations

import pytest

from app.domain.entities import Item
from app.domain.errors import InvalidItemTransition
from app.domain.value_objects import ItemState


def _item(state: ItemState = ItemState.available) -> Item:
    return Item(manifestation_id=1, barcode="B001", state=state, id=1)


def test_allowed_transitions():
    item = _item()
    item.change_state(ItemState.in_repair)
    assert item.state is ItemState.in_repair
    item.change_state(ItemState.available)  # repaired
    assert item.state is ItemState.available
    item.change_state(ItemState.lost)
    item.change_state(ItemState.available)  # found
    assert item.state is ItemState.available


def test_change_to_same_state_is_a_noop():
    item = _item()
    item.change_state(ItemState.available)
    assert item.state is ItemState.available


def test_withdrawn_is_terminal():
    item = _item(ItemState.withdrawn)
    for target in (ItemState.available, ItemState.in_repair, ItemState.lost):
        with pytest.raises(InvalidItemTransition):
            item.change_state(target)


def test_lost_cannot_go_straight_to_in_repair():
    item = _item(ItemState.lost)
    with pytest.raises(InvalidItemTransition):
        item.change_state(ItemState.in_repair)
