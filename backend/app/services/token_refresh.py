"""Transparent Bearer token refresh on 401.

Provides a helper that wraps SmartFlow API calls: if a call gets a 401, it
attempts to refresh the bearer_token using the stored refresh_token, updates the
session, and retries the call once. If the refresh itself fails, raises HTTP 401
to force re-login.

This replicates the behaviour of the reference haulage bot's TokenService.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from app import app_state
from app.services import identity_service
from app.session_store import SessionData

logger = logging.getLogger("simulator.token_refresh")


async def ensure_fresh_token(session: SessionData) -> str:
    """Return a (possibly refreshed) Bearer token for the session.

    Call this before making SmartFlow API requests. If the stored token is still
    valid, it's returned as-is. There's no way to know if it expired without
    trying, so callers should use ``call_with_refresh`` instead for actual API
    calls.
    """
    return session.bearer_token


async def refresh_session_token(session: SessionData) -> str:
    """Attempt to refresh the Bearer token. Returns the new token on success.

    Raises HTTP 401 if the refresh fails (user must re-login).
    """
    if not session.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired and no refresh token available. Please log in again.",
        )

    config = app_state.get_config()
    profile = config.get_profile(session.profile_name) if config else None
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Server profile not found. Please log in again.",
        )

    result = await identity_service.refresh_bearer_token(
        profile, session.refresh_token, session.client_id, session.client_secret
    )

    if result is None:
        # Refresh failed — clear the session tokens and force re-login.
        session.bearer_token = ""
        session.refresh_token = ""
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )

    # Update the session with the new tokens.
    session.bearer_token = result.access_token
    session.refresh_token = result.refresh_token
    logger.info("Refreshed token for user %s", session.username)
    return result.access_token
