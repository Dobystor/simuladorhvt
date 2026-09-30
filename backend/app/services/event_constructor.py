"""Pure logic for building event payloads.

All functions here are stateless (or mutate only the passed-in SessionData),
which makes them independently unit- and property-testable. No network or
database access.

Requirements: 4.2, 4.3, 5.1, 5.2, 6.2, 6.3, 6.4, 7.2, 7.3, 7.4, 7.8, 8.2, 8.3,
              8.5, 9.3, 9.6
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.event_models import (
    CatalogVehicleOperatorAssignmentEvent,
    HaulageVehicleIntegrationEvent,
)
from app.session_store import SessionData

# 18 hours expressed in seconds, used by the Unload 18-hour rule.
EIGHTEEN_HOURS_SECONDS = 18 * 3600
# Weight threshold (tonnes) separating a net load from a tare update.
WEIGHT_THRESHOLD_TONNES = 2.5


# ---------------------------------------------------------------------------
# MAC resolution
# ---------------------------------------------------------------------------


def resolve_mac(swarm_id: str | None, bluetooth_address: str | None) -> str | None:
    """Return uppercase SwarmId if non-empty, else uppercase BluetoothAddress,
    else None."""
    if swarm_id:
        return swarm_id.upper()
    if bluetooth_address:
        return bluetooth_address.upper()
    return None


# ---------------------------------------------------------------------------
# EventId
# ---------------------------------------------------------------------------


def next_event_id(session: SessionData) -> str:
    """Return the current counter as a numeric string, then increment it."""
    eid = session.event_id_counter
    session.event_id_counter += 1
    return str(eid)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def make_dedup_key(date_status: datetime, mac_vehicle: str, status: int) -> tuple:
    """Build the dedup key matching Haulages.API's SHA-256 input format.

    DateStatus is truncated to second-level precision; mac_vehicle is
    normalised to uppercase; status is coerced to int.
    """
    date_str = date_status.strftime("%Y-%m-%d %H:%M:%S")
    return (date_str, mac_vehicle.upper(), int(status))


def is_duplicate(
    session: SessionData, date_status: datetime, mac_vehicle: str, status: int
) -> bool:
    return make_dedup_key(date_status, mac_vehicle, status) in session.published_combos


def record_published_combo(
    session: SessionData, date_status: datetime, mac_vehicle: str, status: int
) -> None:
    session.published_combos.add(make_dedup_key(date_status, mac_vehicle, status))


# ---------------------------------------------------------------------------
# Weighing
# ---------------------------------------------------------------------------


def classify_weighing_result(gross_weight: float, empty_weight: float) -> str:
    """Return "net_load" if abs(gross - empty) > 2.5, else "tare_update"."""
    if abs(gross_weight - empty_weight) > WEIGHT_THRESHOLD_TONNES:
        return "net_load"
    return "tare_update"


def validate_gross_weight(weight: float) -> bool:
    """Return True iff 0 < weight <= 999.99."""
    return 0 < weight <= 999.99


# ---------------------------------------------------------------------------
# Elapsed time / 18-hour rule
# ---------------------------------------------------------------------------


def compute_elapsed_time(load_ts: datetime, reference_ts: datetime) -> tuple[int, int]:
    """Return (hours, minutes) elapsed, truncated to whole minutes."""
    delta = reference_ts - load_ts
    total_secs = int(delta.total_seconds())
    return total_secs // 3600, (total_secs % 3600) // 60


def check_18h_rule(load_ts: datetime, reference_ts: datetime) -> bool:
    """Return True iff more than 18 hours have elapsed (strictly)."""
    return (reference_ts - load_ts).total_seconds() > EIGHTEEN_HOURS_SECONDS


# ---------------------------------------------------------------------------
# Offline date validation
# ---------------------------------------------------------------------------


def validate_offline_date_status(date_status: datetime, now: datetime) -> bool:
    """Return True iff date_status is strictly before now."""
    return date_status < now


# ---------------------------------------------------------------------------
# Event construction
# ---------------------------------------------------------------------------


def _iso_utc(dt: datetime) -> str:
    """Serialize a datetime as UTC ISO 8601 with a trailing 'Z'.

    Haulages.API (.NET) calls ConvertTimeFromUtc on DateStatus, which requires
    DateTimeKind.Utc. A '+00:00' offset is parsed as non-UTC by .NET and throws;
    the 'Z' suffix marks the value as UTC. Emit 'Z' instead of '+00:00'.
    """
    return (
        dt.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def construct_haulage_event(
    session: SessionData,
    status: int,
    mac_vehicle: str,
    mac_beacon: str | None,
    mac_operator: str | None,
    mode: str,
    date_status: datetime | None,
    now: datetime | None = None,
) -> HaulageVehicleIntegrationEvent:
    """Build a HaulageVehicleIntegrationEvent.

    For Online mode: RealTime=True, DateStatus=now (system-assigned).
    For Offline mode: RealTime=False, DateStatus=user-supplied (must be past).

    Raises ValueError if Offline mode is missing/future-dated its DateStatus.
    """
    now = now or datetime.now(timezone.utc)

    if mode == "Online":
        real_time = True
        effective_date_status = now
    elif mode == "Offline":
        if date_status is None:
            raise ValueError("Offline mode requires a DateStatus value")
        if not validate_offline_date_status(date_status, now):
            raise ValueError("Offline DateStatus must be strictly in the past")
        real_time = False
        effective_date_status = date_status
    else:
        raise ValueError(f"Unknown mode: {mode}")

    return HaulageVehicleIntegrationEvent(
        Id=str(uuid.uuid4()),
        CreationDate=_iso_utc(now),
        EventId=next_event_id(session),
        MACVehicle=mac_vehicle.upper(),
        Status=int(status),
        DateStatus=_iso_utc(effective_date_status),
        MACBeacon=(mac_beacon or "").upper(),
        MACOperator=(mac_operator or "").upper(),
        RealTime=real_time,
    )


def construct_operator_assignment_event(
    mac_vehicle: str, mac_operator: str, now: datetime | None = None
) -> CatalogVehicleOperatorAssignmentEvent:
    now = now or datetime.now(timezone.utc)
    return CatalogVehicleOperatorAssignmentEvent(
        Id=str(uuid.uuid4()),
        CreationDate=_iso_utc(now),
        VehicleMAC=mac_vehicle.upper(),
        OperatorMAC=mac_operator.upper(),
    )
