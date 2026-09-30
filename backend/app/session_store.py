"""In-memory session store.

Sessions live in a module-level dict keyed by an opaque session token. No
session data ever touches the SQLite database. The Bearer_Token from SmartFlow
stays server-side and is cleared on logout.

Requirements: 2.2, 2.3, 2.6, 18.5
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import Header, HTTPException, status


@dataclass
class SessionData:
    session_token: str
    username: str
    profile_name: str
    bearer_token: str
    event_id_counter: int = 1
    published_combos: set = field(default_factory=set)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


_sessions: dict[str, SessionData] = {}


def create_session(username: str, profile_name: str, bearer_token: str) -> SessionData:
    token = secrets.token_urlsafe(32)
    session = SessionData(
        session_token=token,
        username=username,
        profile_name=profile_name,
        bearer_token=bearer_token,
    )
    _sessions[token] = session
    return session


def get_session(token: str) -> SessionData | None:
    return _sessions.get(token)


def delete_session(token: str) -> None:
    session = _sessions.pop(token, None)
    if session is not None:
        # Clear the bearer token explicitly (Req 2.6).
        session.bearer_token = ""


def clear_all_sessions() -> None:
    """Test helper: drop all sessions."""
    _sessions.clear()


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


async def get_current_session(
    authorization: str | None = Header(default=None),
) -> SessionData:
    """FastAPI dependency: resolve the session from the Authorization header.

    Raises HTTP 401 if the header is missing/malformed or the token is unknown.
    """
    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    session = get_session(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    return session
