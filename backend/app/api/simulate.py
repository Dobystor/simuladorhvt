"""Simulation API routes.

Covers the haulage events (Load, Unload, WeighingMachine, InTransit, Stop),
location-based unload, and operator assignment. Each route builds the payload,
publishes to RabbitMQ, and writes an audit record to event_log on success.

Requirements: 5.x, 6.x, 7.x, 8.x, 9.x, 10.x, 11.x, 12.x, 15.1, 15.7
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app import app_state, database
from app.background.publisher_manager import PublishError
from app.models.api_models import (
    SimulateHaulageRequest,
    SimulateHaulageResponse,
    SimulateLocationUnloadRequest,
    SimulateLocationUnloadResponse,
    SimulateOperatorAssignRequest,
    SimulateOperatorAssignResponse,
)
from app.models.event_models import StatusHaulageVehicle
from app.services import event_constructor, rethinkdb_service, wrapper_service
from app.session_store import SessionData, get_current_session
from app.websocket import manager as ws_manager

logger = logging.getLogger("simulator.simulate")

router = APIRouter()

HAULAGE_ROUTING_KEY = "HaulageVehicleIntegrationEvent"
OPERATOR_ROUTING_KEY = "CatalogVehicleOperatorAssignmentEvent"

_STATUS_BY_TYPE = {
    "WeighingMachine": StatusHaulageVehicle.WeighingMachine,
    "Load": StatusHaulageVehicle.Load,
    "Unload": StatusHaulageVehicle.Unload,
    "InTransit": StatusHaulageVehicle.InTransit,
    "Stop": StatusHaulageVehicle.Stop,
}


def _require_publisher(profile_name: str):
    publisher = app_state.get_publisher(profile_name)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No publisher available for profile {profile_name}",
        )
    return publisher


async def _write_event_log(record: dict) -> int | None:
    """Insert an event_log row. Logs and returns None on failure (Req 15.7)."""
    try:
        return await database.insert_event_log(record)
    except Exception as exc:  # noqa: BLE001
        logger.error("event_log insert failed: %s", exc)
        return None


@router.post("/haulage", response_model=SimulateHaulageResponse)
async def simulate_haulage(
    body: SimulateHaulageRequest,
    session: SessionData = Depends(get_current_session),
) -> SimulateHaulageResponse:
    now = datetime.now(timezone.utc)
    status_enum = _STATUS_BY_TYPE[body.event_type]

    if not body.mac_vehicle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle has no addressable MAC",
        )

    # Parse Offline DateStatus if supplied.
    date_status_dt: datetime | None = None
    if body.mode == "Offline":
        if not body.date_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Offline mode requires date_status",
            )
        try:
            date_status_dt = datetime.fromisoformat(body.date_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_status is not a valid ISO 8601 datetime",
            )
        if date_status_dt.tzinfo is None:
            date_status_dt = date_status_dt.replace(tzinfo=timezone.utc)
        if not event_constructor.validate_offline_date_status(date_status_dt, now):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Offline date_status must be strictly in the past",
            )

    # Standard weighing validation.
    if body.event_type == "WeighingMachine" and body.weighing_mode == "Standard":
        if body.gross_weight is None or not event_constructor.validate_gross_weight(
            body.gross_weight
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Standard weighing requires 0 < gross_weight <= 999.99",
            )
        if not body.weighing_machine_rethinkdb_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Standard weighing requires weighing_machine_rethinkdb_id",
            )

    # Determine the effective DateStatus for the dedup check.
    effective_date = date_status_dt if body.mode == "Offline" else now
    if event_constructor.is_duplicate(
        session, effective_date, body.mac_vehicle, int(status_enum)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This event would be silently discarded as a duplicate by "
                "Haulages.API (same DateStatus, MACVehicle, and Status)."
            ),
        )

    # Build the event payload.
    try:
        event = event_constructor.construct_haulage_event(
            session,
            status=int(status_enum),
            mac_vehicle=body.mac_vehicle,
            mac_beacon=body.mac_beacon,
            mac_operator=body.mac_operator,
            mode=body.mode,
            date_status=date_status_dt,
            now=now,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )

    # Standard weighing: write RethinkDB weight BEFORE publishing (Req 9.4, 9.9).
    profile = app_state.get_config().get_profile(session.profile_name)
    if body.event_type == "WeighingMachine" and body.weighing_mode == "Standard":
        try:
            await rethinkdb_service.write_weighing_machine_weight(
                profile, body.weighing_machine_rethinkdb_id, body.gross_weight
            )
        except rethinkdb_service.RethinkDBWriteError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )

    # Publish (Req 7.9, 8.7, 9.10, 10.5).
    publisher = _require_publisher(session.profile_name)
    payload = event.to_dict()
    try:
        await publisher.publish(payload, HAULAGE_ROUTING_KEY)
    except PublishError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    # Success: record dedup combo + audit log.
    event_constructor.record_published_combo(
        session, effective_date, body.mac_vehicle, int(status_enum)
    )
    published_at = now.isoformat()
    log_id = await _write_event_log(
        {
            "published_at": published_at,
            "username": session.username,
            "server_profile": session.profile_name,
            "event_type": body.event_type,
            "mac_vehicle": event.MACVehicle,
            "mac_beacon": event.MACBeacon or None,
            "mac_operator": event.MACOperator or None,
            "simulation_mode": body.mode,
            "weighing_mode": body.weighing_mode,
            "gross_weight": body.gross_weight,
            "date_status": event.DateStatus,
            "payload": json.dumps(payload),
        }
    )

    await ws_manager.broadcast(
        session.profile_name,
        {
            "type": "event_published",
            "data": {
                "event_log_id": log_id,
                "event_id": event.EventId,
                "event_type": body.event_type,
                "mac_vehicle": event.MACVehicle,
                "published_at": published_at,
            },
        },
    )

    return SimulateHaulageResponse(
        event_log_id=log_id or 0,
        event_id=event.EventId,
        published_at=published_at,
    )


@router.post("/location-unload", response_model=SimulateLocationUnloadResponse)
async def simulate_location_unload(
    body: SimulateLocationUnloadRequest,
    session: SessionData = Depends(get_current_session),
) -> SimulateLocationUnloadResponse:
    profile = app_state.get_config().get_profile(session.profile_name)
    try:
        await wrapper_service.post_location_unload(
            profile, session.bearer_token, body.vehicle_id, body.reference_point_id
        )
    except wrapper_service.WrapperAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        )

    now = datetime.now(timezone.utc).isoformat()
    log_id = await _write_event_log(
        {
            "published_at": now,
            "username": session.username,
            "server_profile": session.profile_name,
            "event_type": "LocationBasedUnload",
            "mac_vehicle": None,
            "payload": json.dumps(
                {
                    "VehicleId": body.vehicle_id,
                    "HaulageSiteId": body.haulage_site_id,
                    "ReferencePointId": body.reference_point_id,
                    "IsUsedLocation": True,
                }
            ),
        }
    )
    return SimulateLocationUnloadResponse(
        event_log_id=log_id or 0, published_at=now
    )


@router.post("/operator-assign", response_model=SimulateOperatorAssignResponse)
async def simulate_operator_assign(
    body: SimulateOperatorAssignRequest,
    session: SessionData = Depends(get_current_session),
) -> SimulateOperatorAssignResponse:
    if not body.mac_vehicle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="mac_vehicle is missing"
        )
    if not body.mac_operator:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="mac_operator is missing"
        )

    event = event_constructor.construct_operator_assignment_event(
        body.mac_vehicle, body.mac_operator
    )
    payload = event.to_dict()

    publisher = _require_publisher(session.profile_name)
    try:
        await publisher.publish(payload, OPERATOR_ROUTING_KEY)
    except PublishError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    now = datetime.now(timezone.utc).isoformat()
    log_id = await _write_event_log(
        {
            "published_at": now,
            "username": session.username,
            "server_profile": session.profile_name,
            "event_type": "OperatorAssignment",
            "mac_vehicle": event.VehicleMAC,
            "mac_operator": event.OperatorMAC,
            "payload": json.dumps(payload),
        }
    )
    return SimulateOperatorAssignResponse(
        event_log_id=log_id or 0, published_at=now
    )
