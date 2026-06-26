from __future__ import annotations

from datetime import date

from tests.api.conftest import catalog_a_book
from tests.conftest import FixedClock


def _register(client, card="C001", category="general"):
    return client.post(
        "/patrons", json={"card_number": card, "category": category}
    )


def test_checkout_happy_path_returns_201_and_due_date(client):
    catalog_a_book(client)
    _register(client)

    resp = client.post(
        "/loans", json={"item_barcode": "B001", "patron_card": "C001"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["item_barcode"] == "B001"
    assert body["due_date"] == "2026-07-10"  # 2026-06-26 + 14 (general/book)
    assert body["renewal_count"] == 0

    avail = client.get("/items/B001")
    assert avail.status_code == 200
    assert avail.json()["availability"] == "on_loan"


def test_double_checkout_returns_409(client):
    catalog_a_book(client)
    _register(client)
    client.post("/loans", json={"item_barcode": "B001", "patron_card": "C001"})

    resp = client.post(
        "/loans", json={"item_barcode": "B001", "patron_card": "C001"}
    )
    assert resp.status_code == 409
    assert resp.json()["error"] == "ItemNotAvailable"


def test_not_for_loan_returns_422(client):
    catalog_a_book(client, material="reference")
    _register(client)

    resp = client.post(
        "/loans", json={"item_barcode": "B001", "patron_card": "C001"}
    )
    assert resp.status_code == 422
    assert resp.json()["error"] == "NotForLoan"


def test_checkout_unknown_item_returns_404(client):
    _register(client)
    resp = client.post(
        "/loans", json={"item_barcode": "NOPE", "patron_card": "C001"}
    )
    assert resp.status_code == 404


def test_return_then_available_again(client):
    catalog_a_book(client)
    _register(client)
    client.post("/loans", json={"item_barcode": "B001", "patron_card": "C001"})

    resp = client.post("/loans/B001/return")
    assert resp.status_code == 200
    assert resp.json()["hold_triggered"] is False
    assert client.get("/items/B001").json()["availability"] == "available"


def test_duplicate_card_returns_409(client):
    assert _register(client).status_code == 201
    assert _register(client).status_code == 409


def test_patron_suspend_blocks_checkout_then_reinstate_allows(client):
    catalog_a_book(client)  # B001
    created = _register(client, "C001")
    assert created.status_code == 201
    assert created.json()["status"] == "active"
    assert created.json()["expires_on"] is None

    suspended = client.post("/patrons/C001/suspend")
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"

    blocked = client.post(
        "/loans", json={"item_barcode": "B001", "patron_card": "C001"}
    )
    assert blocked.status_code == 422
    assert blocked.json()["error"] == "PatronSuspended"

    reinstated = client.post("/patrons/C001/reinstate")
    assert reinstated.json()["status"] == "active"
    ok = client.post(
        "/loans", json={"item_barcode": "B001", "patron_card": "C001"}
    )
    assert ok.status_code == 201


def test_register_with_expiry_blocks_expired_checkout(client):
    catalog_a_book(client)  # B001; client clock is 2026-06-26
    created = client.post(
        "/patrons",
        json={
            "card_number": "C001",
            "category": "general",
            "expires_on": "2026-06-20",
        },
    )
    assert created.status_code == 201
    assert created.json()["expires_on"] == "2026-06-20"

    blocked = client.post(
        "/loans", json={"item_barcode": "B001", "patron_card": "C001"}
    )
    assert blocked.status_code == 422
    assert blocked.json()["error"] == "PatronExpired"


def test_suspend_unknown_patron_returns_404(client):
    assert client.post("/patrons/NOPE/suspend").status_code == 404


def test_renew_while_suspended_returns_422(client):
    catalog_a_book(client)  # B001
    _register(client, "C001")
    client.post("/loans", json={"item_barcode": "B001", "patron_card": "C001"})
    client.post("/patrons/C001/suspend")

    resp = client.post("/loans/B001/renew")
    assert resp.status_code == 422
    assert resp.json()["error"] == "PatronSuspended"


def test_expire_holds_endpoint(client):
    mid = catalog_a_book(client)
    _register(client, "C001")
    _register(client, "C002")
    client.post("/loans", json={"item_barcode": "B001", "patron_card": "C001"})
    client.post("/holds", json={"manifestation_id": mid, "patron_card": "C002"})
    client.post("/loans/B001/return")  # readied for C002, pickup_by = today + 7
    assert client.get("/items/B001").json()["availability"] == "on_hold_shelf"

    # Advance the app clock past the pickup window, then sweep.
    client.app.state.clock = FixedClock(date(2026, 7, 10))
    resp = client.post("/holds/expire")
    assert resp.status_code == 200
    assert resp.json() == {"expired": 1, "reassigned": 0}
    assert client.get("/items/B001").json()["availability"] == "available"
