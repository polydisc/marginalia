from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import FixedClock


@pytest.fixture
def client(session_factory):
    app = create_app(session_factory)
    app.state.clock = FixedClock()  # deterministic due dates in API tests
    return TestClient(app)


def catalog_a_book(client, *, material: str = "book", barcode: str = "B001"):
    work = client.post("/works", json={"title": "Kokoro", "author": "Soseki"})
    man = client.post(
        "/manifestations",
        json={
            "work_id": work.json()["id"],
            "title": "Kokoro",
            "material_type": material,
        },
    )
    mid = man.json()["id"]
    client.post(f"/manifestations/{mid}/items", json={"barcode": barcode})
    return mid
