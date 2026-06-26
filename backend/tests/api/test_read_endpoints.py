from __future__ import annotations

from datetime import date

from tests.api.conftest import catalog_a_book
from tests.conftest import FixedClock


def _register(client, card="C001", category="general"):
    return client.post(
        "/patrons", json={"card_number": card, "category": category}
    )


def test_catalog_returns_work_tree_with_derived_availability(client):
    catalog_a_book(client)  # B001 under one work/manifestation
    _register(client)

    catalog = client.get("/catalog")
    assert catalog.status_code == 200
    works = catalog.json()
    assert len(works) == 1
    work = works[0]
    assert work["title"] == "Kokoro"
    item = work["manifestations"][0]["items"][0]
    assert item["barcode"] == "B001"
    assert item["availability"] == "available"

    # Once on loan, the catalog tree reflects the derived state.
    client.post("/loans", json={"item_barcode": "B001", "patron_card": "C001"})
    again = client.get("/catalog").json()
    assert again[0]["manifestations"][0]["items"][0]["availability"] == "on_loan"


def test_patron_loans_lists_open_loans_enriched(client):
    catalog_a_book(client)
    _register(client)
    client.post("/loans", json={"item_barcode": "B001", "patron_card": "C001"})

    loans = client.get("/patrons/C001/loans")
    assert loans.status_code == 200
    body = loans.json()
    assert len(body) == 1
    line = body[0]
    assert line["item_barcode"] == "B001"
    assert line["title"] == "Kokoro"
    assert line["renewal_count"] == 0
    assert line["overdue"] is False


def test_ready_holds_lists_the_hold_shelf(client):
    mid = catalog_a_book(client)
    _register(client, "C001")
    _register(client, "C002")
    client.post("/loans", json={"item_barcode": "B001", "patron_card": "C001"})
    client.post("/holds", json={"manifestation_id": mid, "patron_card": "C002"})
    client.post("/loans/B001/return")  # readies the hold for C002

    ready = client.get("/holds/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert len(body) == 1
    assert body[0]["title"] == "Kokoro"
    assert body[0]["patron_card"] == "C002"
    assert body[0]["item_barcode"] == "B001"


def test_patron_loans_empty_when_none(client):
    _register(client)
    assert client.get("/patrons/C001/loans").json() == []


def test_nested_patron_reads_404_for_unknown_card(client):
    # A typo/stale OPAC card should not be indistinguishable from a real empty
    # account; nested resources now mirror GET /patrons/{card}.
    assert client.get("/patrons/NOPE/loans").status_code == 404
    assert client.get("/patrons/NOPE/holds").status_code == 404


def test_patron_loans_overdue_follows_the_injected_clock(client):
    catalog_a_book(client)
    _register(client)
    client.post("/loans", json={"item_barcode": "B001", "patron_card": "C001"})
    assert client.get("/patrons/C001/loans").json()[0]["overdue"] is False

    # Advance the app clock well past the due date — the read model reflects it.
    client.app.state.clock = FixedClock(date(2026, 9, 1))
    assert client.get("/patrons/C001/loans").json()[0]["overdue"] is True


def test_get_patron_returns_profile_and_404(client):
    _register(client, "C001", "student")
    got = client.get("/patrons/C001")
    assert got.status_code == 200
    assert got.json()["category"] == "student"
    assert got.json()["status"] == "active"
    assert client.get("/patrons/NOPE").status_code == 404
