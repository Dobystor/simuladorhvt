"""Entity fetching and client-side filtering.

Fetches the entity types concurrently from Catalog.API and Haulages.API through
the SmartFlow nginx facade (/service/{catalog,haulages}/...). Responses use
mixed casing (Catalog=PascalCase, Haulages=camelCase); a normalization layer
converts them to the snake_case shape the rest of the app and the pure filter
functions expect.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

from __future__ import annotations

import asyncio

import httpx

ENTITY_TIMEOUT_SECONDS = 30.0

# SmartFlow endpoints (relative to profile.api_base_url), discovered against the
# live server. Catalog returns PascalCase; Haulages returns camelCase.
ENDPOINTS = {
    "vehicles": "/service/catalog/api/v1/vehicles/all",
    "haulage_vehicles": "/service/haulages/api/v2/generalsettings/vehicles/all",
    "employees": "/service/catalog/api/v1/employees/all",
    "beacons": "/service/catalog/api/v1/beacons/all",
    "haulage_sites": "/service/haulages/api/v2/HaulageSites/all",
    "weighing_machines": "/service/haulages/api/v2/weighingmachines/all",
}

# HaulageSite.siteType values (confirmed against live data: 0=Load, 1=Unload).
SITE_TYPE_LOAD = 0
SITE_TYPE_UNLOAD = 1


# ---------------------------------------------------------------------------
# Pure filter functions (property-tested — operate on normalized snake_case)
# ---------------------------------------------------------------------------


def filter_vehicles(vehicles: list[dict], haulage_vehicle_ids: set[int]) -> list[dict]:
    """Keep vehicles whose type is 4 or 5 AND that have a HaulageVehicle record.

    Note: this does NOT filter by tag — vehicles without a tag are kept so the
    UI can flag them (has_tag=False) instead of silently hiding them.
    """
    return [
        v
        for v in vehicles
        if v.get("type") in {4, 5} and v.get("id") in haulage_vehicle_ids
    ]


def resolve_vehicle_mac(vehicle: dict) -> str | None:
    """Resolve a vehicle's MAC from its SmartFlowTag (uppercase), or None."""
    tag = vehicle.get("smart_flow_tag") or {}
    return _resolve_mac(tag.get("swarm_id"), tag.get("bluetooth_address"))


def resolve_employee_mac(employee: dict) -> str | None:
    """Resolve an employee's MAC from its first usable tag (uppercase)."""
    for tag in employee.get("smart_flow_tags", []):
        mac = _resolve_mac(tag.get("swarm_id"), tag.get("bluetooth_address"))
        if mac:
            return mac
    return None


def _resolve_mac(swarm_id: str | None, bluetooth_address: str | None) -> str | None:
    if swarm_id:
        return swarm_id.upper()
    if bluetooth_address:
        return bluetooth_address.upper()
    return None


def filter_employees(employees: list[dict]) -> list[dict]:
    """Keep employees with at least one tag having a non-empty swarm_id or
    bluetooth_address."""

    def has_valid_tag(emp: dict) -> bool:
        return any(
            bool(tag.get("swarm_id") or tag.get("bluetooth_address"))
            for tag in emp.get("smart_flow_tags", [])
        )

    return [e for e in employees if has_valid_tag(e)]


def filter_beacons(
    beacons: list[dict],
    haulage_site_ref_ids: set[int],
    weighing_machine_ref_ids: set[int],
) -> list[dict]:
    """Keep beacons whose reference_point_id is in the union of the two ref sets."""
    valid_refs = haulage_site_ref_ids | weighing_machine_ref_ids
    return [b for b in beacons if b.get("reference_point_id") in valid_refs]


# ---------------------------------------------------------------------------
# Normalization (SmartFlow raw -> snake_case app shape)
# ---------------------------------------------------------------------------


def _tag_from_smartflowtag(sft: dict | None) -> dict | None:
    if not sft:
        return None
    return {
        "swarm_id": sft.get("SwarmId"),
        "bluetooth_address": sft.get("BluetoothAddress"),
    }


def normalize_vehicle(v: dict) -> dict:
    return {
        "id": v.get("VehicleId"),
        "name": v.get("EconomicNumber") or str(v.get("VehicleId")),
        "type": v.get("VehicleTypeId"),
        "empty_weight": _to_float(v.get("EmptyWeight")),
        "smart_flow_tag": _tag_from_smartflowtag(v.get("SmartFlowTag")),
    }


def normalize_employee(e: dict) -> dict:
    sft = e.get("SmartFlowTag")
    tags = [_tag_from_smartflowtag(sft)] if sft else []
    return {
        "id": e.get("EmployeeId"),
        "name": e.get("FullName") or e.get("Name") or str(e.get("EmployeeId")),
        "smart_flow_tags": [t for t in tags if t],
    }


def normalize_beacon(b: dict) -> dict:
    return {
        "id": b.get("BeaconId"),
        "mac": b.get("MAC") or "",
        "name": b.get("Name") or "",
        "reference_point_id": b.get("ReferencePointId"),
    }


def normalize_haulage_site(s: dict) -> dict:
    site_type = s.get("siteType")
    type_label = (
        "Load" if site_type == SITE_TYPE_LOAD
        else "Unload" if site_type == SITE_TYPE_UNLOAD
        else str(site_type)
    )
    return {
        "id": s.get("haulageSiteId"),
        "name": s.get("placeName") or str(s.get("haulageSiteId")),
        "type": type_label,
        "reference_point_id": s.get("referencePointId"),
    }


def normalize_weighing_machine(w: dict) -> dict:
    return {
        "id": w.get("weighingMachineId"),
        "name": w.get("name") or str(w.get("weighingMachineId")),
        "reference_point_id": w.get("referencePointId"),
        # Not exposed by the API; used only for Standard weighing writes.
        "rethinkdb_id": str(w.get("weighingMachineId") or ""),
        "simulated_enabled": bool(w.get("isEnabled")),
    }


def haulage_vehicle_ids(haulage_vehicles: list[dict]) -> set[int]:
    """Extract the set of vehicleIds that have a HaulageVehicle record."""
    ids = set()
    for hv in haulage_vehicles:
        vid = hv.get("vehicleId") or hv.get("VehicleId")
        if vid is not None:
            ids.add(vid)
    return ids


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Concurrent fetching
# ---------------------------------------------------------------------------


async def _get_json(
    client: httpx.AsyncClient, base_url: str, path: str, bearer_token: str
):
    resp = await client.get(
        f"{base_url}{path}",
        headers={"Authorization": f"Bearer {bearer_token}"},
        timeout=ENTITY_TIMEOUT_SECONDS,
        follow_redirects=False,
    )
    resp.raise_for_status()
    return resp.json()


async def fetch_all_entities(profile, bearer_token: str) -> dict:
    """Fetch all entity types concurrently.

    Returns a dict with keys: vehicles, employees, beacons, haulage_sites,
    weighing_machines, haulage_vehicles, and errors (map of entityType -> msg).
    Values are RAW SmartFlow payloads; the API layer normalizes and filters.
    Successfully fetched entities are always retained even if others fail.
    """
    base = profile.api_base_url.rstrip("/")
    errors: dict[str, str] = {}

    # verify=False: SmartFlow facade uses an internal/self-signed certificate.
    async with httpx.AsyncClient(verify=False) as client:
        tasks = {
            key: asyncio.create_task(
                _get_json(client, base, path, bearer_token)
            )
            for key, path in ENDPOINTS.items()
        }
        results: dict = {}
        for key, task in tasks.items():
            try:
                results[key] = await task
            except Exception as exc:  # noqa: BLE001 — collect per-type errors
                results[key] = None
                errors[key] = str(exc)

    return {**results, "errors": errors}
