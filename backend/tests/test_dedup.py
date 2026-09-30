"""Property-based tests for dedup round-trip.

Requirements: 5.1, 5.2, 5.4
"""

from datetime import datetime, timezone

from hypothesis import given
from hypothesis import strategies as st

from app.services.event_constructor import (
    is_duplicate,
    make_dedup_key,
    record_published_combo,
)
from app.session_store import SessionData


def _make_session() -> SessionData:
    return SessionData(
        session_token="t", username="u", profile_name="p", bearer_token="b"
    )


mac_text = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), max_codepoint=0x7F),
    min_size=1,
    max_size=12,
)


# Property 6: Dedup round-trip prevents duplicate publication — Req 5.1, 5.2, 5.4
@given(
    dt=st.datetimes(
        min_value=datetime(2000, 1, 1), max_value=datetime(2100, 1, 1)
    ),
    mac=mac_text,
    status=st.integers(min_value=0, max_value=4),
)
def test_dedup_round_trip(dt, mac, status):
    dt = dt.replace(tzinfo=timezone.utc)
    session = _make_session()

    assert is_duplicate(session, dt, mac, status) is False
    record_published_combo(session, dt, mac, status)
    assert is_duplicate(session, dt, mac, status) is True

    # Idempotent second add leaves the set unchanged.
    size = len(session.published_combos)
    record_published_combo(session, dt, mac, status)
    assert len(session.published_combos) == size


@given(
    dt=st.datetimes(
        min_value=datetime(2000, 1, 1), max_value=datetime(2100, 1, 1)
    ),
    mac=mac_text,
    status=st.integers(min_value=0, max_value=4),
)
def test_dedup_case_insensitive(dt, mac, status):
    dt = dt.replace(tzinfo=timezone.utc)
    session = _make_session()
    record_published_combo(session, dt, mac.lower(), status)
    # Reading with upper-case mac still matches.
    assert is_duplicate(session, dt, mac.upper(), status) is True


@given(
    dt=st.datetimes(),
    mac=mac_text,
    status=st.integers(min_value=0, max_value=4),
)
def test_dedup_key_truncates_to_second(dt, mac, status):
    key = make_dedup_key(dt, mac, status)
    # date component has no sub-second precision
    assert "." not in key[0]
    assert key[1] == mac.upper()
    assert key[2] == status
