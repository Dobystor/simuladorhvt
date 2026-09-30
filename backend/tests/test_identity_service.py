"""Unit tests for the Identity service using mocked httpx transport.

Requirements: 2.1, 2.4, 2.8
"""

import httpx
import pytest

from app.services import identity_service


class _Profile:
    api_base_url = "https://id.example.com"


def _patch_transport(monkeypatch, handler):
    """Patch httpx.AsyncClient to use a MockTransport with the given handler."""
    real_init = httpx.AsyncClient.__init__

    def init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", init)


async def test_authenticate_success(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"access_token": "TOKEN123"})

    _patch_transport(monkeypatch, handler)
    token = await identity_service.authenticate(_Profile(), "alice", "pw")
    assert token == "TOKEN123"


async def test_authenticate_401_with_reason(monkeypatch):
    def handler(request):
        return httpx.Response(401, json={"error_description": "bad credentials"})

    _patch_transport(monkeypatch, handler)
    with pytest.raises(identity_service.AuthError) as exc:
        await identity_service.authenticate(_Profile(), "alice", "pw")
    assert "bad credentials" in str(exc.value)


async def test_authenticate_401_generic(monkeypatch):
    def handler(request):
        return httpx.Response(400, json={})

    _patch_transport(monkeypatch, handler)
    with pytest.raises(identity_service.AuthError) as exc:
        await identity_service.authenticate(_Profile(), "alice", "pw")
    assert "Authentication failed" in str(exc.value)


async def test_authenticate_timeout(monkeypatch):
    def handler(request):
        raise httpx.TimeoutException("timed out")

    _patch_transport(monkeypatch, handler)
    with pytest.raises(identity_service.AuthTimeoutError):
        await identity_service.authenticate(_Profile(), "alice", "pw")


async def test_authenticate_unavailable(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("refused")

    _patch_transport(monkeypatch, handler)
    with pytest.raises(identity_service.AuthUnavailableError):
        await identity_service.authenticate(_Profile(), "alice", "pw")
