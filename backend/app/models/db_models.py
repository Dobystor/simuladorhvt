"""TypedDicts matching the SQLite schema column names exactly.

These describe the shape of rows read from / written to the database. They are
intentionally permissive (total=False) for insert helpers that omit optional
columns.

Requirements: 13.2, 15.1
"""

from __future__ import annotations

from typing import TypedDict


class EventLogRow(TypedDict, total=False):
    id: int
    published_at: str      # UTC ISO 8601
    username: str
    server_profile: str
    event_type: str        # Load|Unload|WeighingMachine|InTransit|Stop|
                           #   LocationBasedUnload|OperatorAssignment
    mac_vehicle: str | None
    mac_beacon: str | None
    mac_operator: str | None
    simulation_mode: str | None   # Online|Offline|None
    weighing_mode: str | None     # Standard|SimulatedEnabled|None
    gross_weight: float | None
    date_status: str | None       # UTC ISO 8601
    payload: str                  # full JSON message published


class EventFeedRow(TypedDict, total=False):
    id: int
    received_at: str       # UTC ISO 8601 (Monitor receipt time)
    server_profile: str
    event_id_field: str | None
    mac_vehicle: str | None
    mac_beacon: str | None
    mac_operator: str | None
    status: int | None     # StatusHaulageVehicle int value
    date_status: str | None
    real_time: int | None  # 0 or 1
    is_simulated: int      # 1 if published by this simulator
    raw_payload: str


class UserLastSeenRow(TypedDict, total=False):
    username: str
    server_profile: str
    last_seen: str         # UTC ISO 8601
