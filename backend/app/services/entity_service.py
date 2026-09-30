"""Entity fetching and client-side filtering.

Fetches the five entity types concurrently from Catalog.API and Haulages.API
with a per-request 30-second timeout. Individual failures are collected without
aborting the others. The pure filter functions are property-tested.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

from __future__ import annotations

import asyncio

import httpx

ENTITY_TIMEOUT_SECONDS = 30.0

# SmartFlow endpoints (relative to profile.api_base_url). To be confirmed
# against the live OpenAPI docs.
ENDPOINTS = {
    "vehicles": "/api/v1/Vehicle",
    "haulage_vehicles": "/api/v1/HaulageVehicle",
    "employees": "/api/v1/Employee",
    "beacons": "/api/v1/Beacon",
    "haulage_sites": "/api/v1/HaulageSite",
    "weighing_machines": "/api/v1/WeighingMachine",
}


# ---------------------------------------------------------------------------
# Pure filter functions (property-tested)
# ---------------------------------------------------------------------------


def filter_vehicles(vehicles: list[dict], haulage_vehicle_ids: set[int]) -> list[dict]:
    """Keep vehicles whose type is 4 or 5 AND that have a HaulageVehicle record."""
    return [
        v
        for v in vehicles
        if v.get("type") in {4, 5} and v.get("id") in haulage_vehicle_ids
    ]


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
# Concurrent fetching
# ---------------------------------------------------------------------------


async def _get_json(
    client: httpx.AsyncClient, base_url: str, path: str, bearer_token: str
):
    resp = await client.get(
        f"{base_url}{path}",
        headers={"Authorization": f"Bearer {bearer_token}"},
        timeout=ENTITY_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return resp.json()


async def fetch_all_entities(profile, bearer_token: str) -> dict:
    """Fetch all entity types concurrently.

    Returns a dict with keys: vehicles, employees, beacons, haulage_sites,
    weighing_machines, haulage_vehicles, and errors (map of entityType -> msg).
    Successfully fetched entities are always retained even if others fail.
    """
    base = profile.api_base_url.rstrip("/")
    errors: dict[str, str] = {}

    async with httpx.AsyncClient() as client:
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
