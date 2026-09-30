"""SmartFlow Identity.API authentication.

Posts an OAuth2 password grant to the Identity endpoint with a 10-second
timeout. Returns the access token on success; raises dedicated errors on
timeout or connection failure so the route can map them to 408/503.

Requirements: 2.1, 2.4, 2.8, 18.4
"""

from __future__ import annotations

import httpx

AUTH_TIMEOUT_SECONDS = 10.0
TOKEN_PATH = "/connect/token"


class AuthError(Exception):
    """Authentication failed with a reason (mapped to HTTP 401)."""


class AuthTimeoutError(Exception):
    """The Identity.API request did not complete within the timeout (408)."""


class AuthUnavailableError(Exception):
    """The Identity.API could not be reached (503)."""


async def authenticate(profile, username: str, password: str) -> str:
    """Authenticate against Identity.API and return the Bearer access token.

    Raises AuthError, AuthTimeoutError, or AuthUnavailableError.
    """
    base = profile.api_base_url.rstrip("/")
    url = f"{base}{TOKEN_PATH}"
    data = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "scope": "openid profile",
    }

    try:
        async with httpx.AsyncClient(timeout=AUTH_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, data=data)
    except httpx.TimeoutException:
        raise AuthTimeoutError("Authentication request timed out")
    except httpx.HTTPError as exc:
        raise AuthUnavailableError(f"Cannot reach Identity.API: {exc}")

    if resp.status_code == 200:
        body = resp.json()
        token = body.get("access_token")
        if not token:
            raise AuthError("Identity.API returned no access_token")
        return token

    if 400 <= resp.status_code < 500:
        reason = _extract_error(resp)
        raise AuthError(reason)

    raise AuthUnavailableError(
        f"Identity.API returned unexpected status {resp.status_code}"
    )


def _extract_error(resp: httpx.Response) -> str:
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        return "Authentication failed"
    return (
        body.get("error_description")
        or body.get("error")
        or "Authentication failed"
    )
