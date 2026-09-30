"""Shared application-level state set at startup.

Holds the loaded configuration and the per-profile PublisherManager instances so
API routes can reach them without circular imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.background.publisher_manager import PublisherManager
    from app.config import SimulatorConfig

config: "SimulatorConfig | None" = None
publishers: dict[str, "PublisherManager"] = {}


def set_config(cfg) -> None:
    global config
    config = cfg


def get_config():
    return config


def register_publisher(profile_name: str, publisher) -> None:
    publishers[profile_name] = publisher


def get_publisher(profile_name: str):
    return publishers.get(profile_name)
