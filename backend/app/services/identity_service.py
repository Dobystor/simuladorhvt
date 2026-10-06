"""SmartFlow Identity.API authentication with token refresh.

Uses the OAuth2 password grant for initial login, and refresh_token grant for
transparent token renewal. Client credentials are tried in order (first that
works wins), replicating the reference haulage bot.

Requirements: 2.1, 2.4, 2.5, 2.8
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger("simulator.identity")

AUTH_TIMEOUT_SECONDS = 10.0


class AuthError(Exception):
    """Authentication failed with a reason (mapped to HTTP 401)."""


class AuthTimeoutError(Exception):
    """The Identity.API request did not complete within the timeout (408)."""


class AuthUnavailableError(Exception):
    """The Identity.API could not be reached (503)."""


@dataclass
class AuthResult:
    access_token: str
    refresh_token: str
    client_id: str
    client_secret: str


async def authenticate(profile, username: str, password: str) -> AuthResult:
    """Authenticate against Identity.API and return tokens + winning client.

    Tries each configured OAuth client in order. Raises AuthError,
    AuthTimeoutError, or AuthUnavailableError.
    """
    base = profile.api_base_url.rstrip("/")
    url = f"{base}{profile.token_path}"

    last_error: str | None = None
    reached_server = False

    async with httpx.AsyncClient(
        timeout=AUTH_TIMEOUT_SECONDS, verify=False
    ) as client:
        for oauth in profile.oauth_clients:
            data = {
                "grant_type": "password",
                "username": username,
                "password": password,
                "scope": profile.oauth_scope,
                "client_id": oauth.client_id,
                "client_secret": oauth.client_secret,
            }
            try:
                resp = await client.post(
                    url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            except httpx.TimeoutException:
                raise AuthTimeoutError("Authentication request timed out")
            except httpx.HTTPError as exc:
                last_error = f"Cannot reach Identity.API: {exc}"
                continue

            reached_server = True

            if resp.status_code == 200:
                body = resp.json()
                token = body.get("access_token")
                if token:
                    logger.info(
                        "Authenticated %s with client_id=%s",
                        username,
                        oauth.client_id,
                    )
                    return AuthResult(
                        access_token=token,
                        refresh_token=body.get("refresh_token", ""),
                        client_id=oauth.client_id,
                        client_secret=oauth.client_secret,
                    )
                last_error = "Identity.API returned no access_token"
                continue

            reason = _extract_error(resp)
            last_error = reason
            logger.warning(
                "Auth attempt failed (client_id=%s, status=%s): %s",
                oauth.client_id,
                resp.status_code,
                reason,
            )
            if "invalid_client" not in reason.lower():
                raise AuthError(reason)

    if not reached_server:
        raise AuthUnavailableError(last_error or "Cannot reach Identity.API")
    raise AuthError(last_error or "Authentication failed")


async def refresh_bearer_token(
    profile, refresh_token: str, client_id: str, client_secret: str
) -> AuthResult | None:
    """Use a refresh_token to obtain a new bearer without re-authenticating.

    Returns a new AuthResult on success, or None if the refresh failed (caller
    should force re-login).
    """
    base = profile.api_base_url.rstrip("/")
    url = f"{base}{profile.token_path}"

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    try:
        async with httpx.AsyncClient(
            timeout=AUTH_TIMEOUT_SECONDS, verify=False
        ) as client:
            resp = await client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Token refresh failed (network): %s", exc)
        return None

    if resp.status_code != 200:
        logger.warning(
            "Token refresh failed (%s): %s", resp.status_code, resp.text[:200]
        )
        return None

    body = resp.json()
    new_token = body.get("access_token")
    if not new_token:
        return None

    logger.info("Token refreshed successfully for client_id=%s", client_id)
    return AuthResult(
        access_token=new_token,
        refresh_token=body.get("refresh_token", refresh_token),
        client_id=client_id,
        client_secret=client_secret,
    )


def _extract_error(resp: httpx.Response) -> str:
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        return resp.text or "Authentication failed"
    return (
        body.get("error_description")
        or body.get("error")
        or "Authentication failed"
    )
