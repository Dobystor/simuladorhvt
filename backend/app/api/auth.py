"""Authentication API routes.

Requirements: 1.7, 2.1, 2.3, 2.6, 2.7, 2.8
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app import app_state, database
from app.api.servers import get_dynamic_profile
from app.models.api_models import LoginRequest, LoginResponse
from app.services import identity_service
from app.session_store import (
    SessionData,
    create_session,
    delete_session,
    get_current_session,
)

router = APIRouter()


def _resolve_profile(profile_name: str):
    """Find a profile by name in config.yaml or dynamic servers."""
    config = app_state.get_config()
    if config:
        p = config.get_profile(profile_name)
        if p:
            return p
    return get_dynamic_profile(profile_name)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    config = app_state.get_config()
    profile = _resolve_profile(body.profile_name)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown profile: {body.profile_name}",
        )

    try:
        result = await identity_service.authenticate(
            profile, body.username, body.password
        )
    except identity_service.AuthTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=str(exc)
        )
    except identity_service.AuthUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    except identity_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        )

    session = create_session(body.username, body.profile_name, result.access_token)
    session.refresh_token = result.refresh_token
    session.client_id = result.client_id
    session.client_secret = result.client_secret

    # Record last_seen; failure must not block login (Req 14.6).
    try:
        await database.upsert_user_last_seen(
            body.username, body.profile_name, datetime.now(timezone.utc)
        )
    except Exception:  # noqa: BLE001
        pass

    return LoginResponse(session_token=session.session_token, username=body.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(session: SessionData = Depends(get_current_session)) -> Response:
    delete_session(session.session_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
