"""FastAPI application factory, lifespan, and mounts.

Loads config (exits on failure), initialises the database, and starts one
Monitor and one PublisherManager per Server_Profile as asyncio tasks. Registers
all API routers, the WebSocket endpoint, and mounts the compiled SPA last so API
routes take precedence.

Requirements: 1.1, 13.1, 17.1, 17.2, 17.3
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import app_state, database
from app.api import auth, entities, history, profiles, simulate, summary
from app.background.monitor import Monitor
from app.background.publisher_manager import PublisherManager
from app.config import load_config_or_exit
from app.websocket.endpoint import websocket_endpoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simulator.main")

# Path to the compiled SPA; may not exist during backend-only development.
_FRONTEND_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend",
    "dist",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config_or_exit()
    app_state.set_config(config)

    db_path = os.environ.get("SIMULATOR_DB", "simulator.sqlite")
    await database.init_db(db_path)

    tasks: list[asyncio.Task] = []
    monitors: list[Monitor] = []
    publishers: list[PublisherManager] = []

    for profile in config.server_profiles:
        publisher = PublisherManager(profile)
        app_state.register_publisher(profile.name, publisher)
        publishers.append(publisher)
        tasks.append(asyncio.create_task(publisher.run()))

        monitor = Monitor(profile)
        monitors.append(monitor)
        tasks.append(asyncio.create_task(monitor.run()))

    logger.info(
        "Started %d monitor(s) and %d publisher(s)", len(monitors), len(publishers)
    )

    try:
        yield
    finally:
        for m in monitors:
            await m.stop()
        for p in publishers:
            await p.stop()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def create_app() -> FastAPI:
    app = FastAPI(title="Haulage Event Simulator", lifespan=lifespan)

    app.include_router(auth.router, prefix="/api/auth")
    app.include_router(profiles.router, prefix="/api")
    app.include_router(entities.router, prefix="/api")
    app.include_router(simulate.router, prefix="/api/simulate")
    app.include_router(history.router, prefix="/api/history")
    app.include_router(summary.router, prefix="/api")

    app.add_websocket_route("/ws", websocket_endpoint)

    # Mount the SPA last so /api and /ws take precedence. Only mount if built.
    if os.path.isdir(_FRONTEND_DIST):
        app.mount(
            "/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="spa"
        )
    else:
        logger.warning(
            "Frontend dist not found at %s; SPA will not be served", _FRONTEND_DIST
        )

    return app


app = create_app()
