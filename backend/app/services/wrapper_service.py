"""Wrapper.API location POST for location-based unload simulation.

Requirements: 11.2, 11.3, 11.4
"""

from __future__ import annotations

import httpx

WRAPPER_TIMEOUT_SECONDS = 30.0
LOCATION_PATH = "/api/v1/Location/"


class WrapperAPIError(Exception):
    """Raised when the Wrapper.API request fails or returns a non-2xx status."""


async def post_location_unload(
    profile, bearer_token: str, vehicle_id: int, reference_point_id: int
) -> None:
    """POST a LocationVehicle payload to Wrapper.API.

    Raises WrapperAPIError on timeout, connection error, or non-2xx response.
    """
    base = profile.api_base_url.rstrip("/")
    url = f"{base}{LOCATION_PATH}"
    payload = {
        "VehicleId": vehicle_id,
        "ReferencePointId": reference_point_id,
        "IsUsedLocation": True,
    }
    headers = {"Authorization": f"Bearer {bearer_token}"}

    try:
        async with httpx.AsyncClient(timeout=WRAPPER_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException:
        raise WrapperAPIError("Wrapper.API request timed out")
    except httpx.HTTPError as exc:
        raise WrapperAPIError(f"Cannot reach Wrapper.API: {exc}")

    if not (200 <= resp.status_code < 300):
        raise WrapperAPIError(
            f"Wrapper.API returned {resp.status_code}: {resp.text}"
        )
