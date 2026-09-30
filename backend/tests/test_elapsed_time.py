"""Property-based tests for elapsed time and the 18-hour rule.

Requirements: 8.3, 8.5
"""

from datetime import datetime, timedelta, timezone

from hypothesis import given
from hypothesis import strategies as st

from app.services.event_constructor import check_18h_rule, compute_elapsed_time


# Property 12: Elapsed time and 18-hour rule computation — Req 8.3, 8.5
@given(
    load=st.datetimes(
        min_value=datetime(2000, 1, 1), max_value=datetime(2100, 1, 1)
    ),
    elapsed_seconds=st.integers(min_value=0, max_value=5_000_000),
)
def test_compute_elapsed_time(load, elapsed_seconds):
    load = load.replace(tzinfo=timezone.utc)
    reference = load + timedelta(seconds=elapsed_seconds)

    hours, minutes = compute_elapsed_time(load, reference)
    total_minutes = int((reference - load).total_seconds()) // 60
    assert hours * 60 + minutes == total_minutes
    assert 0 <= minutes < 60


@given(
    load=st.datetimes(
        min_value=datetime(2000, 1, 1), max_value=datetime(2100, 1, 1)
    ),
    elapsed_seconds=st.integers(min_value=0, max_value=5_000_000),
)
def test_check_18h_rule(load, elapsed_seconds):
    load = load.replace(tzinfo=timezone.utc)
    reference = load + timedelta(seconds=elapsed_seconds)
    assert check_18h_rule(load, reference) is (elapsed_seconds > 64800)


def test_18h_rule_boundary():
    load = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert check_18h_rule(load, load + timedelta(seconds=64800)) is False
    assert check_18h_rule(load, load + timedelta(seconds=64801)) is True
