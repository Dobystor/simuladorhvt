"""History API routes with pure filter/sort/paginate helpers.

Requirements: 15.3, 15.4, 15.5, 15.6
"""

from __future__ import annotations

import math

from fastapi import APIRouter

from app import database
from app.models.api_models import (
    EventFeedRecord,
    EventLogRecord,
    HistoryFeedResponse,
    HistoryLogsResponse,
)

router = APIRouter()

PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# Pure helpers (property-tested)
# ---------------------------------------------------------------------------


def filter_event_log(
    records: list[dict],
    username: str | None = None,
    mac_vehicle: str | None = None,
    from_dt: str | None = None,
    to_dt: str | None = None,
    event_type: str | None = None,
) -> list[dict]:
    """Return records matching every active (non-None) filter (AND semantics).

    Date bounds are inclusive and compared lexicographically on ISO 8601
    strings (which sort chronologically).
    """
    result = []
    for r in records:
        if username is not None and r.get("username") != username:
            continue
        if mac_vehicle is not None and r.get("mac_vehicle") != mac_vehicle:
            continue
        if event_type is not None and r.get("event_type") != event_type:
            continue
        published = r.get("published_at") or ""
        if from_dt is not None and published < from_dt:
            continue
        if to_dt is not None and published > to_dt:
            continue
        result.append(r)
    return result


def filter_event_feed(
    records: list[dict],
    profile_name: str | None = None,
    mac_vehicle: str | None = None,
    from_dt: str | None = None,
    to_dt: str | None = None,
) -> list[dict]:
    result = []
    for r in records:
        if profile_name is not None and r.get("server_profile") != profile_name:
            continue
        if mac_vehicle is not None and r.get("mac_vehicle") != mac_vehicle:
            continue
        received = r.get("received_at") or ""
        if from_dt is not None and received < from_dt:
            continue
        if to_dt is not None and received > to_dt:
            continue
        result.append(r)
    return result


def sort_reverse_chronological(records: list[dict], key: str) -> list[dict]:
    """Return records sorted descending by the given timestamp key."""
    return sorted(records, key=lambda r: r.get(key) or "", reverse=True)


def paginate(
    records: list[dict], page: int, page_size: int = PAGE_SIZE
) -> tuple[list[dict], int]:
    """Return (page_records, total). Pages are 1-indexed."""
    total = len(records)
    if page < 1:
        page = 1
    start = (page - 1) * page_size
    end = start + page_size
    return records[start:end], total


def page_count(total: int, page_size: int = PAGE_SIZE) -> int:
    return math.ceil(total / page_size) if total else 0


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/logs", response_model=HistoryLogsResponse)
async def get_logs(
    username: str | None = None,
    mac_vehicle: str | None = None,
    from_dt: str | None = None,
    to_dt: str | None = None,
    event_type: str | None = None,
    page: int = 1,
) -> HistoryLogsResponse:
    rows = await database.fetch_event_log()
    filtered = filter_event_log(
        rows, username, mac_vehicle, from_dt, to_dt, event_type
    )
    ordered = sort_reverse_chronological(filtered, "published_at")
    page_rows, total = paginate(ordered, page)
    return HistoryLogsResponse(
        total=total,
        page=max(page, 1),
        page_size=PAGE_SIZE,
        records=[EventLogRecord(**r) for r in page_rows],
    )


@router.get("/feed", response_model=HistoryFeedResponse)
async def get_feed(
    profile_name: str | None = None,
    mac_vehicle: str | None = None,
    from_dt: str | None = None,
    to_dt: str | None = None,
    page: int = 1,
) -> HistoryFeedResponse:
    rows = await database.fetch_event_feed()
    filtered = filter_event_feed(rows, profile_name, mac_vehicle, from_dt, to_dt)
    ordered = sort_reverse_chronological(filtered, "received_at")
    page_rows, total = paginate(ordered, page)
    return HistoryFeedResponse(
        total=total,
        page=max(page, 1),
        page_size=PAGE_SIZE,
        records=[EventFeedRecord(**r) for r in page_rows],
    )
