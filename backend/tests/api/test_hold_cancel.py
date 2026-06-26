from __future__ import annotations

from tests.api.conftest import catalog_a_book


def _register(client, card):
    return client.post(
        "/patrons", json={"card_number": card, "category": "general"}
    )


def test_patron_holds_listing_and_cancel(client):
    mid = catalog_a_book(client)  # B001
    _register(client, "C001")
    _register(client, "C002")
    client.post("/loans", json={"item_barcode": "B001", "patron_card": "C001"})
    placed = client.post(
        "/holds", json={"manifestation_id": mid, "patron_card": "C002"}
    )
    hold_id = placed.json()["hold_id"]

    holds = client.get("/patrons/C002/holds")
    assert holds.status_code == 200
    body = holds.json()
    assert len(body) == 1
    assert body[0]["hold_id"] == hold_id
    assert body[0]["status"] == "pending"
    assert body[0]["title"] == "Kokoro"

    cancelled = client.post(f"/holds/{hold_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.get("/patrons/C002/holds").json() == []


def test_duplicate_open_hold_returns_409(client):
    mid = catalog_a_book(client)  # B001
    _register(client, "C001")

    first = client.post(
        "/holds", json={"manifestation_id": mid, "patron_card": "C001"}
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/holds", json={"manifestation_id": mid, "patron_card": "C001"}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"] == "DuplicateHold"


def test_cancel_unknown_hold_returns_404(client):
    assert client.post("/holds/999/cancel").status_code == 404
