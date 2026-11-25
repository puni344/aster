import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from backend import main


@pytest.fixture
def app(tmp_path, monkeypatch):
    path = tmp_path / "http.sqlite"
    monkeypatch.setenv("ASTER_DB", str(path))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with TestClient(main.app) as client:
        yield client, path


def test_missing_configuration_and_masked_dashboard(app):
    client, path = app
    data = client.get("/api/dashboard").json()
    assert set(data["missing"]) == {"ELEVENLABS_API_KEY", "GEMINI_API_KEY"}
    assert len(data["doctors"]) == 6 and data["appointments"] == []
    assert (
        client.post("/api/offer", json={"type": "offer", "sdp": "fixture"}).status_code
        == 503
    )
    clinic = main.app.state.clinic
    slot = clinic.available("asha", date="tomorrow")["slots"][0]["slot_id"]
    clinic.mutate("book", slot, "+919876543210", "fixture")
    data = client.get("/api/dashboard").json()
    assert data["appointments"][0]["phone"].endswith("3210")
    assert "9876543210" not in str(data)
    with closing(sqlite3.connect(path)) as db:
        assert (
            db.execute("select max(id) from events").fetchone()[0] == data["revision"]
        )


def test_invalid_date_and_closed_peer_are_explicit(app):
    client, _ = app
    assert client.get("/api/dashboard?day=2027-02-29").status_code == 422
    assert (
        client.patch(
            "/api/offer", json={"pc_id": "ended", "candidates": []}
        ).status_code
        == 404
    )
    assert client.get("/api/events?after=-1").status_code == 422
