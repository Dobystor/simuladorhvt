"""SmartFlow Identity.API authentication.

Uses the OAuth2 password grant against IdentityServer, sending client_id and
client_secret. Client credentials are tried in the order configured on the
profile (first that works wins), replicating the behaviour of the reference
haulage bot that authenticates against this same SmartFlow.

Endpoint (relative to api_base_url): /api/openid/connect/token
Scope: "smartflow IdentityServerApi offline_access"

Requirements: 2.1, 2.4, 2.8, 18.4
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("simulator.identity")

AUTH_TIMEOUT_SECONDS = 10.0


class AuthError(Exception):
    """Authentication failed with a reason (mapped to HTTP 401)."""


class AuthTimeoutError(Exception):
    """The Identity.API request did not complete within the timeout (408)."""


class AuthUnavailableError(Exception):
    """The Identity.API could not be reached (503)."""


async def authenticate(profile, username: str, password: str) -> str:
    """Authenticate against Identity.API and return the Bearer access token.

    Tries each configured OAuth client in order. Raises AuthError,
    AuthTimeoutError, or AuthUnavailableError.
    """
    base = profile.api_base_url.rstrip("/")
    url = f"{base}{profile.token_path}"

    last_error: str | None = None
    reached_server = False

    # verify=False: SmartFlow uses an internal/self-signed cert on the facade.
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
                    return token
                last_error = "Identity.API returned no access_token"
                continue

            # Non-200: capture the reason and try the next client.
            reason = _extract_error(resp)
            last_error = reason
            logger.warning(
                "Auth attempt failed (client_id=%s, status=%s): %s",
                oauth.client_id,
                resp.status_code,
                reason,
            )
            # invalid_client → wrong client creds, try the next candidate.
            # Other errors (e.g. invalid_grant = bad user/pass) are terminal.
            if "invalid_client" not in reason.lower():
                raise AuthError(reason)

    if not reached_server:
        raise AuthUnavailableError(last_error or "Cannot reach Identity.API")
    raise AuthError(last_error or "Authentication failed")


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
