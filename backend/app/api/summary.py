"""Post-login summary API route with pure window/grouping helpers.

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app import database
from app.models.api_models import SummaryEvent, SummaryGroup, SummaryResponse
from app.session_store import SessionData, get_current_session

router = APIRouter()


# ---------------------------------------------------------------------------
# Pure helpers (property-tested)
# ---------------------------------------------------------------------------


def get_events_since(records: list[dict], last_seen: str) -> list[dict]:
    """Return records whose received_at is strictly greater than last_seen."""
    return [r for r in records if (r.get("received_at") or "") > last_seen]


def group_by_mac_vehicle(records: list[dict]) -> list[dict]:
    """Group records by mac_vehicle; groups ordered ascending by mac_vehicle."""
    groups: dict[str, list[dict]] = {}
    for r in records:
        key = r.get("mac_vehicle") or ""
        groups.setdefault(key, []).append(r)
    return [
        {"mac_vehicle": key, "events": groups[key]}
        for key in sorted(groups.keys())
    ]


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    session: SessionData = Depends(get_current_session),
) -> SummaryResponse:
    last_seen = await database.get_user_last_seen(
        session.username, session.profile_name
    )
    if last_seen is None:
        # First-time login: 24-hour window (Req 14.4).
        since_dt = datetime.now(timezone.utc) - timedelta(hours=24)
    else:
        since_dt = last_seen
    since_iso = since_dt.isoformat()

    rows = await database.fetch_event_feed(session.profile_name)
    recent = get_events_since(rows, since_iso)
    grouped = group_by_mac_vehicle(recent)

    groups = [
        SummaryGroup(
            mac_vehicle=g["mac_vehicle"],
            events=[
                SummaryEvent(
                    received_at=e.get("received_at"),
                    status=e.get("status"),
                    mac_beacon=e.get("mac_beacon"),
                    is_simulated=bool(e.get("is_simulated")),
                )
                for e in g["events"]
            ],
        )
        for g in grouped
    ]
    return SummaryResponse(since=since_iso, groups=groups)
