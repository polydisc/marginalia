"""Reachable not-found / duplicate / blocked branches across the use cases.

The happy paths and the headline domain rules are covered elsewhere; this file
pins the "sad path" guards that the API surfaces as 4xx, so a refactor that drops
one is caught here rather than only at the HTTP edge.
"""

from __future__ import annotations

import pytest

from app.application.use_cases.catalog import (
    AddItem,
    CatalogManifestation,
    ChangeItemState,
    GetItemAvailability,
)
from app.application.use_cases.circulation import (
    CheckIn,
    CheckOut,
    PlaceHold,
    RenewLoan,
)
from app.application.use_cases.patrons import RegisterPatron, ReinstatePatron
from app.domain.errors import (
    DuplicateBarcode,
    ItemNotAvailable,
    ItemNotFound,
    LoanNotOpen,
    ManifestationNotFound,
    PatronNotFound,
    WorkNotFound,
)
from app.domain.value_objects import ItemState, MaterialType, PatronCategory
from tests.conftest import seed


# --- catalog ----------------------------------------------------------------


def test_catalog_manifestation_under_unknown_work_raises(uow):
    with pytest.raises(WorkNotFound):
        CatalogManifestation(uow).execute(
            work_id=999, title="Ghost", material_type=MaterialType.book
        )


def test_add_item_to_unknown_manifestation_raises(uow):
    with pytest.raises(ManifestationNotFound):
        AddItem(uow).execute(999, "Z001")


def test_add_item_with_duplicate_barcode_raises(uow):
    s = seed(uow)
    with pytest.raises(DuplicateBarcode):
        AddItem(uow).execute(s.manifestation_id, s.item_barcode)


def test_item_availability_for_unknown_barcode_raises(uow):
    with pytest.raises(ItemNotFound):
        GetItemAvailability(uow).execute("NOPE")


def test_change_state_blocked_while_set_aside_for_a_ready_hold(uow, policy, clock):
    s = seed(uow)
    RegisterPatron(uow).execute("C002", PatronCategory.general)
    CheckOut(uow, policy, clock).execute(s.item_barcode, s.patron_card)
    PlaceHold(uow, clock).execute(s.manifestation_id, "C002")
    # Returning the only copy sets it aside (ready) for the waiting patron.
    result = CheckIn(uow, clock, 7).execute(s.item_barcode)
    assert result.hold_triggered

    with pytest.raises(ItemNotAvailable):
        ChangeItemState(uow).execute(s.item_barcode, ItemState.in_repair)


# --- patrons ----------------------------------------------------------------


def test_reinstate_unknown_patron_raises(uow):
    with pytest.raises(PatronNotFound):
        ReinstatePatron(uow).execute("GHOST")


# --- circulation ------------------------------------------------------------


def test_checkout_for_unknown_patron_raises(uow, policy, clock):
    s = seed(uow)
    with pytest.raises(PatronNotFound):
        CheckOut(uow, policy, clock).execute(s.item_barcode, "GHOST")


def test_checkin_unknown_item_raises(uow, clock):
    with pytest.raises(ItemNotFound):
        CheckIn(uow, clock, 7).execute("NOPE")


def test_renew_unknown_item_raises(uow, policy, clock):
    with pytest.raises(ItemNotFound):
        RenewLoan(uow, policy, clock).execute("NOPE")


def test_renew_item_not_on_loan_raises(uow, policy, clock):
    s = seed(uow)
    with pytest.raises(LoanNotOpen):
        RenewLoan(uow, policy, clock).execute(s.item_barcode)


def test_place_hold_on_unknown_manifestation_raises(uow, clock):
    s = seed(uow)
    with pytest.raises(ManifestationNotFound):
        PlaceHold(uow, clock).execute(999, s.patron_card)


def test_place_hold_for_unknown_patron_raises(uow, clock):
    s = seed(uow)
    with pytest.raises(PatronNotFound):
        PlaceHold(uow, clock).execute(s.manifestation_id, "GHOST")
