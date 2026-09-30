"""Profiles API route.

Requirements: 1.3
"""

from __future__ import annotations

from fastapi import APIRouter

from app import app_state
from app.models.api_models import ProfileInfo

router = APIRouter()


@router.get("/profiles", response_model=list[ProfileInfo])
async def list_profiles() -> list[ProfileInfo]:
    config = app_state.get_config()
    if config is None:
        return []
    return [
        ProfileInfo(name=p.name, api_base_url=p.api_base_url)
        for p in config.server_profiles
    ]
