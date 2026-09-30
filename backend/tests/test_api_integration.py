"""Integration tests for the FastAPI app wiring.

Exercises login -> simulate -> history/summary with RabbitMQ, Identity, and the
background tasks mocked. Uses an in-memory-ish temp SQLite DB.

Requirements: 2.x, 7.x, 15.x
"""

from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app import app_state, database, session_store
from app.config import ServerProfile, SimulatorConfig
from app.main import create_app


class _FakePublisher:
    def __init__(self):
        self.published = []

    async def publish(self, payload, routing_key):
        self.published.append((payload, routing_key))


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Build a config with a single profile.
    profile = ServerProfile(
        name="Local",
        api_base_url="https://id.example.com",
        rabbitmq={"host": "h", "username": "u", "password": "p"},
        rethinkdb={"host": "h"},
    )
    config = SimulatorConfig(server_profiles=[profile])

    # Prevent the lifespan from loading config / starting background tasks.
    monkeypatch.setattr("app.main.load_config_or_exit", lambda: config)
    monkeypatch.setattr(
        "app.main.PublisherManager",
        lambda p: type(
            "P", (), {"run": AsyncMock(), "stop": AsyncMock()}
        )(),
    )
    monkeypatch.setattr(
        "app.main.Monitor",
        lambda p: type("M", (), {"run": AsyncMock(), "stop": AsyncMock()})(),
    )

    db_path = str(tmp_path / "it.sqlite")
    monkeypatch.setenv("SIMULATOR_DB", db_path)
    database.configure_db_path(db_path)

    session_store.clear_all_sessions()

    app = create_app()
    with TestClient(app) as c:
        # Register a fake publisher for the profile.
        app_state.register_publisher("Local", _FakePublisher())
        yield c


def _login(client, monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"access_token": "TOKEN"})

    real_init = httpx.AsyncClient.__init__

    def init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", init)

    resp = client.post(
        "/api/auth/login",
        json={"profile_name": "Local", "username": "alice", "password": "pw"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["session_token"]


def test_profiles_endpoint(client):
    resp = client.get("/api/profiles")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "Local"


def test_login_and_simulate_load(client, monkeypatch):
    token = _login(client, monkeypatch)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/simulate/haulage",
        headers=headers,
        json={
            "event_type": "Load",
            "mac_vehicle": "aa:bb",
            "mac_beacon": "cc:dd",
            "mode": "Online",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["event_id"] == "1"
    assert body["event_log_id"] >= 1

    # The published payload reached the fake publisher.
    publisher = app_state.get_publisher("Local")
    assert len(publisher.published) == 1
    payload, routing_key = publisher.published[0]
    assert routing_key == "HaulageVehicleIntegrationEvent"
    assert payload["MACVehicle"] == "AA:BB"
    assert payload["Status"] == 1
    assert payload["RealTime"] is True


def test_duplicate_rejected(client, monkeypatch):
    token = _login(client, monkeypatch)
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "event_type": "Load",
        "mac_vehicle": "AA",
        "mac_beacon": "BB",
        "mode": "Offline",
        "date_status": "2020-01-01T00:00:00+00:00",
    }
    first = client.post("/api/simulate/haulage", headers=headers, json=body)
    assert first.status_code == 200
    second = client.post("/api/simulate/haulage", headers=headers, json=body)
    assert second.status_code == 409


def test_history_logs_after_simulation(client, monkeypatch):
    token = _login(client, monkeypatch)
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/api/simulate/haulage",
        headers=headers,
        json={
            "event_type": "Stop",
            "mac_vehicle": "AA",
            "mode": "Online",
        },
    )
    resp = client.get("/api/history/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["records"][0]["event_type"] == "Stop"


def test_summary_first_login_uses_24h_window(client, monkeypatch):
    token = _login(client, monkeypatch)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/summary", headers=headers)
    assert resp.status_code == 200
    assert "since" in resp.json()


def test_offline_accepts_z_suffix_iso(client, monkeypatch):
    """date_status with a trailing 'Z' (JS toISOString) must be accepted."""
    token = _login(client, monkeypatch)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/simulate/haulage",
        headers=headers,
        json={
            "event_type": "Load",
            "mac_vehicle": "ZZ",
            "mac_beacon": "BB",
            "mode": "Offline",
            "date_status": "2020-01-01T00:00:00.000Z",
        },
    )
    assert resp.status_code == 200, resp.text


def test_operator_assign_missing_mac(client, monkeypatch):
    token = _login(client, monkeypatch)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/simulate/operator-assign",
        headers=headers,
        json={"mac_vehicle": "AA", "mac_operator": ""},
    )
    assert resp.status_code == 400
