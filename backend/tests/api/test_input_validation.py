from __future__ import annotations

# The interface layer bounds free-text request fields (schemas.py) so a request
# body cannot carry an empty or unbounded string past the boundary. FastAPI
# rejects a violation with 422 before any use case runs.


def test_empty_title_is_rejected(client):
    r = client.post("/works", json={"title": "", "author": "Sōseki N."})
    assert r.status_code == 422


def test_whitespace_title_is_rejected(client):
    r = client.post("/works", json={"title": "   ", "author": "Sōseki N."})
    assert r.status_code == 422


def test_oversized_title_is_rejected(client):
    r = client.post("/works", json={"title": "x" * 256, "author": "y"})
    assert r.status_code == 422


def test_surrounding_whitespace_is_trimmed_at_the_boundary(client):
    r = client.post(
        "/works", json={"title": "  Kokoro  ", "author": "  Sōseki N.  "}
    )
    assert r.status_code == 201
    assert r.json()["title"] == "Kokoro"
    assert r.json()["author"] == "Sōseki N."


def test_oversized_card_number_is_rejected(client):
    r = client.post(
        "/patrons", json={"card_number": "C" * 65, "category": "general"}
    )
    assert r.status_code == 422


def test_oversized_path_barcode_is_rejected(client):
    # Path params bypass request-body schemas, so routers must carry their own
    # bounds to protect arbitrary API clients, not just the bundled SPA.
    r = client.get(f"/items/{'B' * 65}")
    assert r.status_code == 422


def test_out_of_range_path_id_is_rejected(client):
    # An id beyond the 64-bit DB range must fail validation, not overflow the
    # lookup into a 500.
    huge = 10**40
    r = client.post(f"/holds/{huge}/cancel")
    assert r.status_code == 422


def test_out_of_range_body_id_is_rejected(client):
    huge = 10**40
    r = client.post("/holds", json={"manifestation_id": huge, "patron_card": "C001"})
    assert r.status_code == 422


def test_valid_input_still_accepted(client):
    r = client.post("/works", json={"title": "Kokoro", "author": "Sōseki N."})
    assert r.status_code == 201
