from __future__ import annotations

from datetime import date

from tests.api.conftest import catalog_a_book
from tests.conftest import FixedClock


def _register(client, card="C001", category="general"):
    return client.post(
        "/patrons", json={"card_number": card, "category": category}
    )


def test_update_work_title_and_author(client):
    mid = catalog_a_book(client)
    work = client.get("/catalog").json()[0]
    resp = client.put(
        f"/works/{work['id']}",
        json={"title": "Kokoro (rev)", "author": "Sōseki N."},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Kokoro (rev)"
    again = client.get("/catalog").json()[0]
    assert again["title"] == "Kokoro (rev)"
    assert again["author"] == "Sōseki N."
    assert again["manifestations"][0]["id"] == mid


def test_update_manifestation_fields(client):
    mid = catalog_a_book(client)
    resp = client.put(
        f"/manifestations/{mid}",
        json={
            "title": "Kokoro",
            "material_type": "audiovisual",
            "isbn": "978-0000000000",
            "publisher": "Audible",
        },
    )
    assert resp.status_code == 200
    m = client.get("/catalog").json()[0]["manifestations"][0]
    assert m["material_type"] == "audiovisual"
    assert m["isbn"] == "978-0000000000"
    assert m["publisher"] == "Audible"


def test_update_patron_category_and_expiry_blocks_when_expired(client):
    catalog_a_book(client)  # B001
    _register(client, "C001", "general")

    resp = client.put(
        "/patrons/C001",
        json={"category": "student", "expires_on": "2026-06-20"},
    )
    assert resp.status_code == 200
    assert resp.json()["category"] == "student"
    assert client.get("/patrons/C001").json()["expires_on"] == "2026-06-20"

    # Clock is 2026-06-26 -> the new expiry is in the past -> checkout blocked.
    client.app.state.clock = FixedClock(date(2026, 6, 26))
    blocked = client.post(
        "/loans", json={"item_barcode": "B001", "patron_card": "C001"}
    )
    assert blocked.status_code == 422
    assert blocked.json()["error"] == "PatronExpired"


def test_update_unknown_records_404(client):
    r = client.put("/works/999", json={"title": "x", "author": "y"})
    assert r.status_code == 404
    assert (
        client.put(
            "/manifestations/999",
            json={"title": "x", "material_type": "book"},
        ).status_code
        == 404
    )
    assert (
        client.put(
            "/patrons/NOPE", json={"category": "general"}
        ).status_code
        == 404
    )
