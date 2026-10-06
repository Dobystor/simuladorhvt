"""Pydantic request and response models for the REST API.

Requirements: 2.1, 3.1, 7.1, 8.1, 9.1, 10.1, 11.1, 12.1, 13.1, 14.1, 15.1
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Auth & profiles
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    profile_name: str
    username: str
    password: str


class LoginResponse(BaseModel):
    session_token: str
    username: str


class ProfileInfo(BaseModel):
    name: str
    api_base_url: str


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


class SmartFlowTagInfo(BaseModel):
    swarm_id: str | None = None
    bluetooth_address: str | None = None


class VehicleInfo(BaseModel):
    id: int
    name: str
    type: int
    empty_weight: float | None = None
    smart_flow_tag: SmartFlowTagInfo | None = None
    mac: str | None = None       # resolved uppercase SwarmId/BluetoothAddress
    has_tag: bool = False        # True when a usable MAC could be resolved


class EmployeeInfo(BaseModel):
    id: int
    name: str
    smart_flow_tags: list[SmartFlowTagInfo] = []
    mac: str | None = None       # resolved uppercase SwarmId/BluetoothAddress
    has_tag: bool = False


class BeaconInfo(BaseModel):
    id: int
    mac: str
    name: str
    reference_point_id: int | None = None


class HaulageSiteInfo(BaseModel):
    id: int
    name: str
    type: str
    reference_point_id: int | None = None


class WeighingMachineInfo(BaseModel):
    id: int
    name: str
    reference_point_id: int | None = None
    rethinkdb_id: str
    simulated_enabled: bool = False


class EntitiesResponse(BaseModel):
    vehicles: list[VehicleInfo] = []
    employees: list[EmployeeInfo] = []
    beacons: list[BeaconInfo] = []
    haulage_sites: list[HaulageSiteInfo] = []
    weighing_machines: list[WeighingMachineInfo] = []
    errors: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


class SimulateHaulageRequest(BaseModel):
    event_type: Literal["Load", "Unload", "WeighingMachine", "InTransit", "Stop"]
    mac_vehicle: str
    mac_beacon: str | None = None
    mac_operator: str | None = None
    mode: Literal["Online", "Offline"]
    date_status: str | None = None       # ISO 8601 UTC — required for Offline
    weighing_mode: Literal["Standard", "SimulatedEnabled"] | None = None
    gross_weight: float | None = None    # required for Standard weighing
    weighing_machine_rethinkdb_id: str | None = None  # required for Standard weighing


class SimulateHaulageResponse(BaseModel):
    event_log_id: int
    event_id: str
    published_at: str


class SimulateLocationUnloadRequest(BaseModel):
    vehicle_id: int
    haulage_site_id: int
    reference_point_id: int


class SimulateLocationUnloadResponse(BaseModel):
    event_log_id: int
    published_at: str


class SimulateOperatorAssignRequest(BaseModel):
    mac_vehicle: str
    mac_operator: str


class SimulateOperatorAssignResponse(BaseModel):
    event_log_id: int
    published_at: str


# ---------------------------------------------------------------------------
# History & summary
# ---------------------------------------------------------------------------


class EventLogRecord(BaseModel):
    id: int
    published_at: str
    username: str
    server_profile: str
    event_type: str
    mac_vehicle: str | None = None
    mac_beacon: str | None = None
    mac_operator: str | None = None
    simulation_mode: str | None = None
    weighing_mode: str | None = None
    gross_weight: float | None = None
    payload: str


class HistoryLogsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    records: list[EventLogRecord]


class EventFeedRecord(BaseModel):
    id: int
    received_at: str
    server_profile: str
    event_id_field: str | None = None
    mac_vehicle: str | None = None
    mac_beacon: str | None = None
    mac_operator: str | None = None
    status: int | None = None
    date_status: str | None = None
    real_time: int | None = None
    is_simulated: int
    raw_payload: str


class HistoryFeedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    records: list[EventFeedRecord]


class SummaryEvent(BaseModel):
    received_at: str
    status: int | None = None
    mac_beacon: str | None = None
    is_simulated: bool


class SummaryGroup(BaseModel):
    mac_vehicle: str
    events: list[SummaryEvent]


class SummaryResponse(BaseModel):
    since: str
    groups: list[SummaryGroup]
