"""Unit tests for the Identity service using mocked httpx transport.

Requirements: 2.1, 2.4, 2.8
"""

import httpx
import pytest

from app.services import identity_service


class _OAuthClient:
    def __init__(self, cid, secret):
        self.client_id = cid
        self.client_secret = secret


class _Profile:
    api_base_url = "https://id.example.com"
    token_path = "/api/openid/connect/token"
    oauth_scope = "smartflow IdentityServerApi offline_access"
    oauth_clients = [
        _OAuthClient("private.networking.app", "UxwYJsELeTnSc2Zz642K"),
        _OAuthClient("smartflow.csharp.client", "secret"),
    ]


def _patch_transport(monkeypatch, handler):
    """Patch httpx.AsyncClient to use a MockTransport with the given handler."""
    real_init = httpx.AsyncClient.__init__

    def init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        kwargs.pop("verify", None)  # MockTransport ignores verify
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", init)


async def test_authenticate_success_first_client(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"access_token": "TOKEN123", "refresh_token": "REF"})

    _patch_transport(monkeypatch, handler)
    result = await identity_service.authenticate(_Profile(), "alice", "pw")
    assert result.access_token == "TOKEN123"
    assert result.refresh_token == "REF"
    assert result.client_id == "private.networking.app"


async def test_authenticate_falls_back_to_second_client(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            # First client rejected as invalid_client -> should try the next.
            return httpx.Response(400, json={"error": "invalid_client"})
        return httpx.Response(200, json={"access_token": "SECOND", "refresh_token": "R2"})

    _patch_transport(monkeypatch, handler)
    result = await identity_service.authenticate(_Profile(), "alice", "pw")
    assert result.access_token == "SECOND"
    assert result.client_id == "smartflow.csharp.client"
    assert calls["n"] == 2


async def test_authenticate_bad_credentials_is_terminal(monkeypatch):
    def handler(request):
        # invalid_grant = wrong user/pass; must not keep trying clients.
        return httpx.Response(400, json={"error_description": "invalid_grant"})

    _patch_transport(monkeypatch, handler)
    with pytest.raises(identity_service.AuthError) as exc:
        await identity_service.authenticate(_Profile(), "alice", "pw")
    assert "invalid_grant" in str(exc.value)


async def test_authenticate_all_clients_invalid(monkeypatch):
    def handler(request):
        return httpx.Response(400, json={"error": "invalid_client"})

    _patch_transport(monkeypatch, handler)
    with pytest.raises(identity_service.AuthError):
        await identity_service.authenticate(_Profile(), "alice", "pw")


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
