"""WebSocket endpoint at /ws?token=<session_token>.

Requirements: 1.4, 16.4
"""

from __future__ import annotations

from fastapi import WebSocket, WebSocketDisconnect

from app.session_store import get_session
from app.websocket import manager as ws_manager


async def websocket_endpoint(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    session = get_session(token) if token else None
    if session is None:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    profile_name = session.profile_name
    ws_manager.connect(websocket, profile_name)

    # Push the current connection status for all profiles on connect.
    for _, status_data in ws_manager.get_all_connection_status().items():
        await websocket.send_json({"type": "connection_status", "data": status_data})

    try:
        while True:
            # We don't expect client messages; just keep the socket open.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        ws_manager.disconnect(websocket, profile_name)
