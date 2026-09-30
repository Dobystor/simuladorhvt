"""Property-based tests for event_log/feed query and summary helpers.

Requirements: 2.7, 15.1, 15.3, 15.4, 15.5, 14.2, 14.3
"""

from datetime import datetime

from hypothesis import given
from hypothesis import strategies as st

from app.api.history import (
    filter_event_log,
    page_count,
    paginate,
    sort_reverse_chronological,
)
from app.api.summary import get_events_since, group_by_mac_vehicle

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

iso_datetime = st.datetimes(
    min_value=datetime(2000, 1, 1), max_value=datetime(2100, 1, 1)
).map(lambda d: d.isoformat())

username_st = st.sampled_from(["alice", "bob", "carol"])
mac_st = st.sampled_from(["AA", "BB", "CC", "DD"])
type_st = st.sampled_from(["Load", "Unload", "WeighingMachine", "Stop"])

log_record = st.fixed_dictionaries(
    {
        "id": st.integers(min_value=1, max_value=10_000),
        "published_at": iso_datetime,
        "username": username_st,
        "server_profile": st.just("Local"),
        "event_type": type_st,
        "mac_vehicle": mac_st,
        "payload": st.just("{}"),
    }
)

feed_record = st.fixed_dictionaries(
    {
        "id": st.integers(min_value=1, max_value=10_000),
        "received_at": iso_datetime,
        "server_profile": st.just("Local"),
        "mac_vehicle": mac_st,
        "is_simulated": st.integers(min_value=0, max_value=1),
        "raw_payload": st.just("{}"),
    }
)


# ---------------------------------------------------------------------------
# Property 14: Event_log filter returns only matching records — Req 15.3
# ---------------------------------------------------------------------------


@given(
    records=st.lists(log_record, max_size=40),
    username=st.one_of(st.none(), username_st),
    mac=st.one_of(st.none(), mac_st),
    etype=st.one_of(st.none(), type_st),
)
def test_filter_event_log_property(records, username, mac, etype):
    result = filter_event_log(records, username=username, mac_vehicle=mac, event_type=etype)

    def matches(r):
        return (
            (username is None or r["username"] == username)
            and (mac is None or r["mac_vehicle"] == mac)
            and (etype is None or r["event_type"] == etype)
        )

    for r in result:
        assert matches(r)
    for r in records:
        if matches(r):
            assert r in result


# ---------------------------------------------------------------------------
# Property 15: Event_log default order is reverse chronological — Req 15.4
# ---------------------------------------------------------------------------


@given(records=st.lists(log_record, max_size=40))
def test_sort_reverse_chronological(records):
    ordered = sort_reverse_chronological(records, "published_at")
    for i in range(len(ordered) - 1):
        assert ordered[i]["published_at"] >= ordered[i + 1]["published_at"]
    assert len(ordered) == len(records)


# ---------------------------------------------------------------------------
# Property 16: Pagination invariant — Req 15.5
# ---------------------------------------------------------------------------


@given(records=st.lists(log_record, max_size=350))
def test_pagination_invariant(records):
    total = len(records)
    pages = page_count(total, page_size=100)
    assert pages == (0 if total == 0 else (total + 99) // 100)

    collected = []
    seen_ids = []
    for p in range(1, max(pages, 1) + 1):
        page_rows, reported_total = paginate(records, p, page_size=100)
        assert reported_total == total
        assert len(page_rows) <= 100
        collected.extend(page_rows)
        seen_ids.extend(id(r) for r in page_rows)

    # Concatenation of all pages equals original order.
    assert collected == records
    # No record appears in more than one page.
    assert len(seen_ids) == len(set(seen_ids))


# ---------------------------------------------------------------------------
# Property 17: Login summary retrieves only events after last_seen — Req 14.2
# ---------------------------------------------------------------------------


@given(records=st.lists(feed_record, max_size=40), last_seen=iso_datetime)
def test_get_events_since(records, last_seen):
    result = get_events_since(records, last_seen)
    for r in result:
        assert r["received_at"] > last_seen
    for r in records:
        if r["received_at"] > last_seen:
            assert r in result
        if r["received_at"] == last_seen:
            assert r not in result


# ---------------------------------------------------------------------------
# Property 18: Login summary groups and orders by MACVehicle ascending — Req 14.3
# ---------------------------------------------------------------------------


@given(records=st.lists(feed_record, max_size=40))
def test_group_by_mac_vehicle(records):
    groups = group_by_mac_vehicle(records)

    # Ascending key order.
    keys = [g["mac_vehicle"] for g in groups]
    assert keys == sorted(keys)

    # Every record in exactly one group, group key matches its members.
    total = 0
    for g in groups:
        for e in g["events"]:
            assert (e.get("mac_vehicle") or "") == g["mac_vehicle"]
        total += len(g["events"])
    assert total == len(records)
