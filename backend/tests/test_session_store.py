"""Unit tests for the in-memory session store.

Requirements: 2.2, 2.3, 2.6
"""

import pytest
from fastapi import HTTPException

from app import session_store


def setup_function():
    session_store.clear_all_sessions()


def test_create_and_get_session():
    s = session_store.create_session("alice", "Local", "BEARER")
    assert s.event_id_counter == 1
    assert s.published_combos == set()
    assert session_store.get_session(s.session_token) is s


def test_delete_session_clears_bearer():
    s = session_store.create_session("alice", "Local", "BEARER")
    token = s.session_token
    session_store.delete_session(token)
    assert session_store.get_session(token) is None
    assert s.bearer_token == ""


async def test_get_current_session_valid():
    s = session_store.create_session("alice", "Local", "BEARER")
    resolved = await session_store.get_current_session(f"Bearer {s.session_token}")
    assert resolved is s


async def test_get_current_session_missing_header():
    with pytest.raises(HTTPException) as exc:
        await session_store.get_current_session(None)
    assert exc.value.status_code == 401


async def test_get_current_session_bad_token():
    with pytest.raises(HTTPException) as exc:
        await session_store.get_current_session("Bearer nope")
    assert exc.value.status_code == 401
