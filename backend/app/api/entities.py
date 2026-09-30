"""Entity loading API routes.

Fetches live entity data from the SmartFlow APIs, applies client-side filters,
and returns typed entities plus a per-type errors map. Successfully loaded
entities are retained even if others fail.

Requirements: 3.1, 3.5, 3.6, 3.7, 3.8
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app import app_state
from app.models.api_models import (
    BeaconInfo,
    EmployeeInfo,
    EntitiesResponse,
    HaulageSiteInfo,
    SmartFlowTagInfo,
    VehicleInfo,
    WeighingMachineInfo,
)
from app.services import entity_service
from app.session_store import SessionData, get_current_session

router = APIRouter()


def _build_response(raw: dict) -> EntitiesResponse:
    """Map raw SmartFlow payloads into filtered, typed entities.

    The raw dict has keys vehicles, haulage_vehicles, employees, beacons,
    haulage_sites, weighing_machines (any may be None on failure) plus errors.
    """
    errors = dict(raw.get("errors", {}))

    vehicles_raw = raw.get("vehicles") or []
    haulage_vehicles_raw = raw.get("haulage_vehicles") or []
    employees_raw = raw.get("employees") or []
    beacons_raw = raw.get("beacons") or []
    haulage_sites_raw = raw.get("haulage_sites") or []
    weighing_machines_raw = raw.get("weighing_machines") or []

    haulage_vehicle_ids = {
        hv.get("vehicle_id", hv.get("id")) for hv in haulage_vehicles_raw
    }
    site_ref_ids = {
        s.get("reference_point_id")
        for s in haulage_sites_raw
        if s.get("reference_point_id") is not None
    }
    wm_ref_ids = {
        w.get("reference_point_id")
        for w in weighing_machines_raw
        if w.get("reference_point_id") is not None
    }

    vehicles = entity_service.filter_vehicles(vehicles_raw, haulage_vehicle_ids)
    employees = entity_service.filter_employees(employees_raw)
    beacons = entity_service.filter_beacons(beacons_raw, site_ref_ids, wm_ref_ids)

    return EntitiesResponse(
        vehicles=[_vehicle(v) for v in vehicles],
        employees=[_employee(e) for e in employees],
        beacons=[_beacon(b) for b in beacons],
        haulage_sites=[_haulage_site(s) for s in haulage_sites_raw],
        weighing_machines=[_weighing_machine(w) for w in weighing_machines_raw],
        errors=errors,
    )


def _tag(t: dict | None) -> SmartFlowTagInfo | None:
    if not t:
        return None
    return SmartFlowTagInfo(
        swarm_id=t.get("swarm_id"), bluetooth_address=t.get("bluetooth_address")
    )


def _vehicle(v: dict) -> VehicleInfo:
    return VehicleInfo(
        id=v["id"],
        name=v.get("name", ""),
        type=v.get("type", 0),
        empty_weight=v.get("empty_weight"),
        smart_flow_tag=_tag(v.get("smart_flow_tag")),
    )


def _employee(e: dict) -> EmployeeInfo:
    return EmployeeInfo(
        id=e["id"],
        name=e.get("name", ""),
        smart_flow_tags=[
            _tag(t) for t in e.get("smart_flow_tags", []) if _tag(t) is not None
        ],
    )


def _beacon(b: dict) -> BeaconInfo:
    return BeaconInfo(
        id=b["id"],
        mac=b.get("mac", ""),
        name=b.get("name", ""),
        reference_point_id=b.get("reference_point_id"),
    )


def _haulage_site(s: dict) -> HaulageSiteInfo:
    return HaulageSiteInfo(
        id=s["id"],
        name=s.get("name", ""),
        type=str(s.get("type", "")),
        reference_point_id=s.get("reference_point_id", 0),
    )


def _weighing_machine(w: dict) -> WeighingMachineInfo:
    return WeighingMachineInfo(
        id=w["id"],
        name=w.get("name", ""),
        reference_point_id=w.get("reference_point_id", 0),
        rethinkdb_id=str(w.get("rethinkdb_id", "")),
        simulated_enabled=bool(w.get("simulated_enabled", False)),
    )


async def _load(session: SessionData) -> EntitiesResponse:
    profile = app_state.get_config().get_profile(session.profile_name)
    raw = await entity_service.fetch_all_entities(profile, session.bearer_token)
    return _build_response(raw)


@router.get("/entities", response_model=EntitiesResponse)
async def get_entities(
    session: SessionData = Depends(get_current_session),
) -> EntitiesResponse:
    return await _load(session)


@router.post("/entities/reload", response_model=EntitiesResponse)
async def reload_entities(
    session: SessionData = Depends(get_current_session),
) -> EntitiesResponse:
    return await _load(session)
