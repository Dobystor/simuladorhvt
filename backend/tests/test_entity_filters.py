"""Property-based tests for entity filter functions.

Requirements: 3.2, 3.3, 3.4
"""

from hypothesis import given
from hypothesis import strategies as st

from app.services.entity_service import (
    filter_beacons,
    filter_employees,
    filter_vehicles,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

vehicle_strategy = st.fixed_dictionaries(
    {
        "id": st.integers(min_value=1, max_value=50),
        "type": st.integers(min_value=0, max_value=7),
        "has_haulage_vehicle": st.booleans(),
    }
)

nullable_id_str = st.one_of(st.none(), st.just(""), st.text(max_size=8))

tag_strategy = st.fixed_dictionaries(
    {"swarm_id": nullable_id_str, "bluetooth_address": nullable_id_str}
)

employee_strategy = st.fixed_dictionaries(
    {
        "id": st.integers(min_value=1, max_value=50),
        "smart_flow_tags": st.lists(tag_strategy, max_size=4),
    }
)

beacon_strategy = st.fixed_dictionaries(
    {
        "id": st.integers(min_value=1, max_value=50),
        "reference_point_id": st.one_of(st.none(), st.integers(min_value=1, max_value=30)),
    }
)


# ---------------------------------------------------------------------------
# Property 1: Vehicle filter correctness — Requirements 3.2
# ---------------------------------------------------------------------------


@given(st.lists(vehicle_strategy, max_size=30))
def test_filter_vehicles_property(vehicles):
    haulage_ids = {v["id"] for v in vehicles if v["has_haulage_vehicle"]}
    result = filter_vehicles(vehicles, haulage_ids)

    # Every returned vehicle satisfies both conditions.
    for v in result:
        assert v["type"] in {4, 5}
        assert v["id"] in haulage_ids

    # Every qualifying vehicle is returned.
    for v in vehicles:
        if v["type"] in {4, 5} and v["id"] in haulage_ids:
            assert v in result


# ---------------------------------------------------------------------------
# Property 2: Employee filter correctness — Requirements 3.3
# ---------------------------------------------------------------------------


@given(st.lists(employee_strategy, max_size=30))
def test_filter_employees_property(employees):
    result = filter_employees(employees)

    def qualifies(emp):
        return any(
            bool(t.get("swarm_id") or t.get("bluetooth_address"))
            for t in emp.get("smart_flow_tags", [])
        )

    for e in result:
        assert qualifies(e)
    for e in employees:
        if qualifies(e):
            assert e in result


# ---------------------------------------------------------------------------
# Property 3: Beacon filter correctness — Requirements 3.4
# ---------------------------------------------------------------------------


@given(
    st.lists(beacon_strategy, max_size=30),
    st.frozensets(st.integers(min_value=1, max_value=30), max_size=10),
    st.frozensets(st.integers(min_value=1, max_value=30), max_size=10),
)
def test_filter_beacons_property(beacons, site_refs, wm_refs):
    result = filter_beacons(beacons, set(site_refs), set(wm_refs))
    union = set(site_refs) | set(wm_refs)

    for b in result:
        assert b["reference_point_id"] in union
    for b in beacons:
        if b["reference_point_id"] in union:
            assert b in result
