"""Property-based tests for EventId, MAC normalization, and mode fields.

Requirements: 4.2, 4.3, 4.4, 6.2, 6.3, 6.4, 7.2, 7.3, 7.4, 7.8, 8.2
"""

import json
from datetime import datetime, timedelta, timezone

from hypothesis import given
from hypothesis import strategies as st

from app.services.event_constructor import (
    construct_haulage_event,
    next_event_id,
    resolve_mac,
    validate_offline_date_status,
)
from app.session_store import SessionData


def _make_session() -> SessionData:
    return SessionData(
        session_token="t",
        username="u",
        profile_name="p",
        bearer_token="b",
    )


# ---------------------------------------------------------------------------
# Property 4: EventId counter produces a strict sequence — Req 4.2, 4.4
# ---------------------------------------------------------------------------


@given(st.integers(min_value=1, max_value=500))
def test_event_id_strict_sequence(n):
    session = _make_session()
    ids = [next_event_id(session) for _ in range(n)]
    assert ids == [str(i) for i in range(1, n + 1)]
    assert len(set(ids)) == n  # no repeats


# ---------------------------------------------------------------------------
# Property 5: EventId serialised as numeric string — Req 4.3
# ---------------------------------------------------------------------------


@given(st.integers(min_value=1, max_value=10_000))
def test_event_id_is_numeric_string(k):
    session = _make_session()
    session.event_id_counter = k
    value = next_event_id(session)
    assert isinstance(value, str)
    assert value.isdigit()
    assert int(value) == k
    # In a JSON payload the field appears as a JSON string.
    payload = json.dumps({"EventId": value})
    assert f'"EventId": "{k}"' in payload


# ---------------------------------------------------------------------------
# Property 7: MAC fields normalised to uppercase — Req 7.2, 7.3, 7.4, 7.8, 8.2
# ---------------------------------------------------------------------------

mixed_case_text = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), max_codepoint=0x7F),
    max_size=12,
)


@given(
    swarm=st.one_of(st.none(), st.just(""), mixed_case_text),
    bt=st.one_of(st.none(), st.just(""), mixed_case_text),
)
def test_resolve_mac_uppercase(swarm, bt):
    result = resolve_mac(swarm, bt)
    if swarm:
        assert result == swarm.upper()
    elif bt:
        assert result == bt.upper()
    else:
        assert result is None


def test_mac_operator_empty_string_when_absent():
    session = _make_session()
    event = construct_haulage_event(
        session,
        status=1,
        mac_vehicle="aa:bb",
        mac_beacon="cc:dd",
        mac_operator=None,
        mode="Online",
        date_status=None,
    )
    assert event.MACOperator == ""
    assert event.MACVehicle == "AA:BB"
    assert event.MACBeacon == "CC:DD"


# ---------------------------------------------------------------------------
# Property 8: Online mode sets RealTime and DateStatus correctly — Req 6.2
# ---------------------------------------------------------------------------


@given(status=st.integers(min_value=0, max_value=4))
def test_online_mode_fields(status):
    session = _make_session()
    before = datetime.now(timezone.utc)
    event = construct_haulage_event(
        session,
        status=status,
        mac_vehicle="AA",
        mac_beacon="BB",
        mac_operator=None,
        mode="Online",
        date_status=None,
    )
    after = datetime.now(timezone.utc)
    assert event.RealTime is True
    ds = datetime.fromisoformat(event.DateStatus)
    assert before - timedelta(seconds=2) <= ds <= after + timedelta(seconds=2)


# ---------------------------------------------------------------------------
# Property 9: Offline mode rejects non-past DateStatus — Req 6.3, 6.4
# ---------------------------------------------------------------------------


@given(offset_seconds=st.integers(min_value=-100_000, max_value=100_000))
def test_offline_date_validation(offset_seconds):
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    candidate = now + timedelta(seconds=offset_seconds)
    expected = candidate < now
    assert validate_offline_date_status(candidate, now) is expected


@given(past_seconds=st.integers(min_value=1, max_value=1_000_000))
def test_offline_mode_uses_supplied_date(past_seconds):
    session = _make_session()
    now = datetime.now(timezone.utc)
    date_status = now - timedelta(seconds=past_seconds)
    event = construct_haulage_event(
        session,
        status=2,
        mac_vehicle="AA",
        mac_beacon="BB",
        mac_operator=None,
        mode="Offline",
        date_status=date_status,
        now=now,
    )
    assert event.RealTime is False
    assert datetime.fromisoformat(event.DateStatus) == date_status
