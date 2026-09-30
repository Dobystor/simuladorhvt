"""WebSocket connection registry and broadcast hub.

A module-level registry maps profile_name -> set[WebSocket]. Background tasks
(Monitor, PublisherManager) call broadcast() to push feed events and
connection-status changes to all connected clients for a profile.

Requirements: 13.2, 16.4
"""

from __future__ import annotations

from fastapi import WebSocket

_connections: dict[str, set[WebSocket]] = {}

# Latest known connection status per profile, pushed to clients on connect.
_connection_status: dict[str, dict] = {}


def connect(ws: WebSocket, profile_name: str) -> None:
    _connections.setdefault(profile_name, set()).add(ws)


def disconnect(ws: WebSocket, profile_name: str) -> None:
    conns = _connections.get(profile_name)
    if conns is not None:
        conns.discard(ws)


def set_connection_status(profile_name: str, status: dict) -> None:
    _connection_status[profile_name] = status


def get_all_connection_status() -> dict[str, dict]:
    return dict(_connection_status)


async def broadcast(profile_name: str, message: dict) -> None:
    """Send a JSON message to all sockets for a profile; drop dead ones."""
    conns = _connections.get(profile_name, set())
    dead: list[WebSocket] = []
    for ws in list(conns):
        try:
            await ws.send_json(message)
        except Exception:  # noqa: BLE001 — stale/closed socket
            dead.append(ws)
    for ws in dead:
        conns.discard(ws)


async def broadcast_connection_status(
    profile_name: str, status: str, retry_in_seconds: int | None = None
) -> None:
    data = {"profile": profile_name, "status": status}
    if retry_in_seconds is not None:
        data["retry_in_seconds"] = retry_in_seconds
    set_connection_status(profile_name, data)
    await broadcast(profile_name, {"type": "connection_status", "data": data})
