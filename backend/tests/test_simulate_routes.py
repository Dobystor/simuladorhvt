"""Integration tests for the simulate routes and event_log completeness.

Uses a fake PublisherManager and an in-memory-ish temp SQLite DB. Validates
Property 13 (event_log records contain all required fields).

Requirements: 2.7, 7.x, 9.x, 12.x, 15.1
"""

import pytest
from fastapi.testclient import TestClient

from app import app_state, database, session_store
from app.api import auth, profiles, simulate, summary
from app.config import ServerProfile, SimulatorConfig
from fastapi import FastAPI


class FakePublisher:
    def __init__(self):
        self.published = []

    async def publish(self, payload, routing_key):
        self.published.append((routing_key, payload))


@pytest.fixture
def client(tmp_path, monkeypatch):
    database.configure_db_path(str(tmp_path / "sim.sqlite"))

    profile = ServerProfile(
        name="Local",
        api_base_url="https://x",
        rabbitmq={"host": "h", "username": "u", "password": "p"},
        rethinkdb={"host": "h"},
    )
    config = SimulatorConfig(server_profiles=[profile])
    app_state.set_config(config)
    fake = FakePublisher()
    app_state.publishers.clear()
    app_state.register_publisher("Local", fake)

    session_store.clear_all_sessions()

    app = FastAPI()
    app.include_router(auth.router, prefix="/api/auth")
    app.include_router(profiles.router, prefix="/api")
    app.include_router(simulate.router, prefix="/api/simulate")
    app.include_router(summary.router, prefix="/api")

    import asyncio

    asyncio.get_event_loop().run_until_complete(database.init_db())

    with TestClient(app) as c:
        c.fake = fake
        yield c


def _make_session():
    return session_store.create_session("alice", "Local", "BEARER")


def _auth_header(session):
    return {"Authorization": f"Bearer {session.session_token}"}


def test_list_profiles(client):
    resp = client.get("/api/profiles")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "Local"


def test_simulate_load_online(client):
    session = _make_session()
    resp = client.post(
        "/api/simulate/haulage",
        headers=_auth_header(session),
        json={
            "event_type": "Load",
            "mac_vehicle": "aa:bb",
            "mac_beacon": "cc:dd",
            "mode": "Online",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["event_id"] == "1"
    assert data["event_log_id"] >= 1
    # Publisher received a persistent message.
    assert client.fake.published[0][0] == "HaulageVehicleIntegrationEvent"
    assert client.fake.published[0][1]["MACVehicle"] == "AA:BB"


def test_duplicate_returns_409(client):
    session = _make_session()
    body = {
        "event_type": "Load",
        "mac_vehicle": "AA:BB",
        "mac_beacon": "CC:DD",
        "mode": "Offline",
        "date_status": "2020-01-01T00:00:00+00:00",
    }
    first = client.post(
        "/api/simulate/haulage", headers=_auth_header(session), json=body
    )
    assert first.status_code == 200, first.text
    second = client.post(
        "/api/simulate/haulage", headers=_auth_header(session), json=body
    )
    assert second.status_code == 409


def test_offline_future_date_rejected(client):
    session = _make_session()
    resp = client.post(
        "/api/simulate/haulage",
        headers=_auth_header(session),
        json={
            "event_type": "Load",
            "mac_vehicle": "AA:BB",
            "mac_beacon": "CC:DD",
            "mode": "Offline",
            "date_status": "2999-01-01T00:00:00+00:00",
        },
    )
    assert resp.status_code == 400


def test_operator_assign_missing_mac(client):
    session = _make_session()
    resp = client.post(
        "/api/simulate/operator-assign",
        headers=_auth_header(session),
        json={"mac_vehicle": "AA:BB", "mac_operator": ""},
    )
    assert resp.status_code == 400


def test_operator_assign_success(client):
    session = _make_session()
    resp = client.post(
        "/api/simulate/operator-assign",
        headers=_auth_header(session),
        json={"mac_vehicle": "aa:bb", "mac_operator": "11:22"},
    )
    assert resp.status_code == 200, resp.text
    routing, payload = client.fake.published[-1]
    assert routing == "CatalogVehicleOperatorAssignmentEvent"
    assert payload["VehicleMAC"] == "AA:BB"
    assert payload["OperatorMAC"] == "11:22"


def test_event_log_completeness_property(client):
    """Property 13: event_log rows have all required non-empty fields."""
    session = _make_session()
    for i, et in enumerate(["Load", "Unload", "InTransit", "Stop"]):
        client.post(
            "/api/simulate/haulage",
            headers=_auth_header(session),
            json={
                "event_type": et,
                "mac_vehicle": f"AA:0{i}",
                "mac_beacon": "CC:DD",
                "mode": "Online",
            },
        )

    import asyncio

    rows = asyncio.get_event_loop().run_until_complete(database.fetch_event_log())
    assert len(rows) == 4
    for row in rows:
        assert row["published_at"]
        assert row["username"] == "alice"
        assert row["server_profile"] == "Local"
        assert row["event_type"]
        assert row["payload"]
