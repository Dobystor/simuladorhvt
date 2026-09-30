"""Event payload models published to RabbitMQ.

Field sources are documented inline: (session) = derived from SessionData,
(user) = user input, (system) = system-generated at construction time.

Requirements: 7.1, 7.5, 10.1, 10.2, 12.1
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import IntEnum
from typing import TypedDict


class StatusHaulageVehicle(IntEnum):
    """StatusHaulageVehicle enum (matches Haulages.API)."""

    WeighingMachine = 0
    Load = 1
    Unload = 2
    InTransit = 3
    Stop = 4


@dataclass
class HaulageVehicleIntegrationEvent:
    """The RabbitMQ integration event consumed by Haulages.API.

    Exchange: smartflow_event_bus (direct, durable)
    Routing key: HaulageVehicleIntegrationEvent
    Delivery mode: persistent; content-type application/json.
    """

    Id: str          # (system) str(uuid.uuid4())
    CreationDate: str  # (system) UTC ISO 8601 at publication
    EventId: str     # (session) str(event_id_counter) before increment
    MACVehicle: str  # (session/user) uppercase SwarmId or BluetoothAddress
    Status: int      # (system) StatusHaulageVehicle int value
    DateStatus: str  # (system for Online, user for Offline) UTC ISO 8601
    MACBeacon: str   # (user) uppercase MAC; empty string for InTransit/Stop
    MACOperator: str  # (user) uppercase; empty string when no employee
    RealTime: bool   # (system) True for Online_Mode, False for Offline_Mode

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class CatalogVehicleOperatorAssignmentEvent:
    """WiFi operator-to-vehicle assignment event.

    Routing key: CatalogVehicleOperatorAssignmentEvent
    """

    Id: str           # (system) str(uuid.uuid4())
    CreationDate: str  # (system) UTC ISO 8601
    VehicleMAC: str   # (user) uppercase
    OperatorMAC: str  # (user) uppercase

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


class LocationVehicle(TypedDict):
    """Payload POSTed to Wrapper.API /api/v1/Location/."""

    VehicleId: int          # (user) selected vehicle's ID
    ReferencePointId: int   # (user) Unload HaulageSite's ReferencePointId
    IsUsedLocation: bool    # (system) always True
