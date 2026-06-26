from __future__ import annotations

from tests.api.conftest import catalog_a_book


def _register(client, card="C001"):
    return client.post(
        "/patrons", json={"card_number": card, "category": "general"}
    )


def test_mark_in_repair_blocks_checkout_then_shelve_allows(client):
    catalog_a_book(client)  # B001
    _register(client)

    repair = client.post("/items/B001/state", json={"state": "in_repair"})
    assert repair.status_code == 200
    assert repair.json()["state"] == "in_repair"
    assert client.get("/items/B001").json()["availability"] == "in_repair"

    blocked = client.post(
        "/loans", json={"item_barcode": "B001", "patron_card": "C001"}
    )
    assert blocked.status_code == 409  # ItemNotAvailable

    # Repaired -> back on the shelf -> loanable again.
    repaired = client.post("/items/B001/state", json={"state": "available"})
    assert repaired.status_code == 200
    ok = client.post(
        "/loans", json={"item_barcode": "B001", "patron_card": "C001"}
    )
    assert ok.status_code == 201


def test_cannot_change_state_while_on_loan(client):
    catalog_a_book(client)
    _register(client)
    client.post("/loans", json={"item_barcode": "B001", "patron_card": "C001"})

    resp = client.post("/items/B001/state", json={"state": "lost"})
    assert resp.status_code == 409
    assert "on loan" in resp.json()["detail"]


def test_invalid_transition_returns_409(client):
    catalog_a_book(client)
    client.post("/items/B001/state", json={"state": "withdrawn"})  # terminal
    resp = client.post("/items/B001/state", json={"state": "available"})
    assert resp.status_code == 409
    assert resp.json()["error"] == "InvalidItemTransition"


def test_unknown_item_state_change_404(client):
    assert client.post("/items/NOPE/state", json={"state": "lost"}).status_code == 404
