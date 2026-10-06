"""Dynamic server management API.

Allows adding/removing SmartFlow servers from the UI without editing
config.yaml. Servers are persisted in SQLite and their Monitor/Publisher
background tasks are started/stopped dynamically.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from app import app_state, database
from app.background.monitor import Monitor
from app.background.publisher_manager import PublisherManager
from app.config import RabbitMQConfig, RethinkDBConfig, ServerProfile

logger = logging.getLogger("simulator.servers")

router = APIRouter()

# Track dynamic tasks so they can be stopped on server deletion.
_dynamic_tasks: dict[str, list[asyncio.Task]] = {}
_dynamic_monitors: dict[str, Monitor] = {}
_dynamic_publishers: dict[str, PublisherManager] = {}


class AddServerRequest(BaseModel):
    name: str
    api_url: str
    rabbitmq_host: str | None = None    # defaults to same as api host
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "smartflow"
    rabbitmq_pass: str = "Sm4rtFl0wN3w"
    rabbitmq_vhost: str = "/"
    rethinkdb_host: str | None = None   # defaults to same as api host
    rethinkdb_port: int = 28115


class ServerInfo(BaseModel):
    id: int | None = None   # None for static (config.yaml) profiles
    name: str
    api_url: str
    source: str             # "config" or "dynamic"


def _extract_host(api_url: str) -> str:
    """Extract the hostname/IP from an API URL."""
    host = api_url.replace("https://", "").replace("http://", "")
    host = host.split("/")[0].split(":")[0]
    return host


def _build_profile(row: dict) -> ServerProfile:
    """Build a ServerProfile from a server_config DB row."""
    return ServerProfile(
        name=row["name"],
        api_base_url=row["api_url"],
        rabbitmq=RabbitMQConfig(
            host=row["rabbitmq_host"],
            port=row["rabbitmq_port"],
            username=row["rabbitmq_user"],
            password=row["rabbitmq_pass"],
            vhost=row["rabbitmq_vhost"],
        ),
        rethinkdb=RethinkDBConfig(
            host=row["rethinkdb_host"],
            port=row["rethinkdb_port"],
        ),
    )


async def start_dynamic_profile(profile: ServerProfile) -> None:
    """Start Monitor and Publisher for a dynamically added server."""
    publisher = PublisherManager(profile)
    monitor = Monitor(profile)
    app_state.register_publisher(profile.name, publisher)
    tasks = [
        asyncio.create_task(publisher.run()),
        asyncio.create_task(monitor.run()),
    ]
    _dynamic_tasks[profile.name] = tasks
    _dynamic_monitors[profile.name] = monitor
    _dynamic_publishers[profile.name] = publisher
    logger.info("Started dynamic profile: %s", profile.name)


async def stop_dynamic_profile(name: str) -> None:
    """Stop Monitor and Publisher for a dynamically removed server."""
    monitor = _dynamic_monitors.pop(name, None)
    publisher = _dynamic_publishers.pop(name, None)
    if monitor:
        await monitor.stop()
    if publisher:
        await publisher.stop()
    for task in _dynamic_tasks.pop(name, []):
        task.cancel()
    app_state.publishers.pop(name, None)
    logger.info("Stopped dynamic profile: %s", name)


async def start_all_dynamic_profiles() -> None:
    """Called at startup to start tasks for all DB-stored servers."""
    rows = await database.list_server_configs()
    for row in rows:
        profile = _build_profile(row)
        await start_dynamic_profile(profile)


def get_dynamic_profile(name: str) -> ServerProfile | None:
    """Look up a dynamic profile by name from the DB cache."""
    pub = _dynamic_publishers.get(name)
    if pub:
        return pub.profile
    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/servers", response_model=list[ServerInfo])
async def list_servers() -> list[ServerInfo]:
    """List all servers (static from config.yaml + dynamic from DB)."""
    servers: list[ServerInfo] = []

    # Static profiles from config.yaml.
    config = app_state.get_config()
    if config:
        for p in config.server_profiles:
            servers.append(ServerInfo(
                name=p.name, api_url=p.api_base_url, source="config"
            ))

    # Dynamic profiles from the database.
    rows = await database.list_server_configs()
    for row in rows:
        servers.append(ServerInfo(
            id=row["id"], name=row["name"], api_url=row["api_url"],
            source="dynamic",
        ))

    return servers


@router.post("/servers", response_model=ServerInfo, status_code=201)
async def add_server(body: AddServerRequest) -> ServerInfo:
    """Register a new server and start its background tasks."""
    api_host = _extract_host(body.api_url)

    # Ensure the URL has a scheme.
    api_url = body.api_url.strip()
    if not api_url.startswith("http"):
        api_url = f"https://{api_url}"

    record = {
        "name": body.name.strip(),
        "api_url": api_url,
        "rabbitmq_host": body.rabbitmq_host or api_host,
        "rabbitmq_port": body.rabbitmq_port,
        "rabbitmq_user": body.rabbitmq_user,
        "rabbitmq_pass": body.rabbitmq_pass,
        "rabbitmq_vhost": body.rabbitmq_vhost,
        "rethinkdb_host": body.rethinkdb_host or api_host,
        "rethinkdb_port": body.rethinkdb_port,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        new_id = await database.insert_server_config(record)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not add server: {exc}",
        )

    profile = _build_profile(record)
    await start_dynamic_profile(profile)

    return ServerInfo(id=new_id, name=record["name"], api_url=api_url, source="dynamic")


@router.delete("/servers/{server_id}")
async def remove_server(server_id: int) -> Response:
    """Remove a dynamic server and stop its background tasks."""
    rows = await database.list_server_configs()
    row = next((r for r in rows if r["id"] == server_id), None)
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")

    await stop_dynamic_profile(row["name"])
    await database.delete_server_config(server_id)
    return Response(status_code=204)
