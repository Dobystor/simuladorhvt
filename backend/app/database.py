"""SQLite database layer using aiosqlite.

Owns the three audit tables (event_log, event_feed, user_last_seen), their
indexes, and a small schema-version table for future migrations. Exposes async
helpers used by the API routes and background tasks. Session state never touches
this database.

Requirements: 13.4, 15.1, 15.2, 14.1
"""

from __future__ import annotations

from datetime import datetime

import aiosqlite

SCHEMA_VERSION = 1

_DDL_STATEMENTS: list[str] = [
    "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);",
    """
    CREATE TABLE IF NOT EXISTS event_log (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        published_at      TEXT    NOT NULL,
        username          TEXT    NOT NULL,
        server_profile    TEXT    NOT NULL,
        event_type        TEXT    NOT NULL,
        mac_vehicle       TEXT,
        mac_beacon        TEXT,
        mac_operator      TEXT,
        simulation_mode   TEXT,
        weighing_mode     TEXT,
        gross_weight      REAL,
        date_status       TEXT,
        payload           TEXT    NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_log_profile   ON event_log(server_profile);",
    "CREATE INDEX IF NOT EXISTS idx_log_vehicle   ON event_log(mac_vehicle);",
    "CREATE INDEX IF NOT EXISTS idx_log_published ON event_log(published_at);",
    "CREATE INDEX IF NOT EXISTS idx_log_username  ON event_log(username);",
    "CREATE INDEX IF NOT EXISTS idx_log_type      ON event_log(event_type);",
    """
    CREATE TABLE IF NOT EXISTS event_feed (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        received_at     TEXT    NOT NULL,
        server_profile  TEXT    NOT NULL,
        event_id_field  TEXT,
        mac_vehicle     TEXT,
        mac_beacon      TEXT,
        mac_operator    TEXT,
        status          INTEGER,
        date_status     TEXT,
        real_time       INTEGER,
        is_simulated    INTEGER NOT NULL,
        raw_payload     TEXT    NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_feed_received ON event_feed(received_at);",
    "CREATE INDEX IF NOT EXISTS idx_feed_profile  ON event_feed(server_profile);",
    "CREATE INDEX IF NOT EXISTS idx_feed_vehicle  ON event_feed(mac_vehicle);",
    """
    CREATE TABLE IF NOT EXISTS user_last_seen (
        username        TEXT    NOT NULL,
        server_profile  TEXT    NOT NULL,
        last_seen       TEXT    NOT NULL,
        PRIMARY KEY (username, server_profile)
    );
    """,
]

# Module-level path so helpers can open short-lived connections. Set by init_db.
_db_path: str = "simulator.sqlite"


def configure_db_path(path: str) -> None:
    """Set the SQLite file path used by all helper connections."""
    global _db_path
    _db_path = path


def get_db_path() -> str:
    return _db_path


async def init_db(path: str | None = None) -> None:
    """Create the schema and indexes if they do not exist (idempotent).

    Called from the FastAPI lifespan at startup.
    """
    if path is not None:
        configure_db_path(path)

    async with aiosqlite.connect(_db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        for statement in _DDL_STATEMENTS:
            await db.execute(statement)
        # Record the schema version once.
        cursor = await db.execute("SELECT version FROM schema_version LIMIT 1;")
        row = await cursor.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO schema_version (version) VALUES (?);", (SCHEMA_VERSION,)
            )
        await db.commit()


async def insert_event_log(record: dict) -> int:
    """Insert an event_log row and return its new id.

    Expected keys: published_at, username, server_profile, event_type,
    mac_vehicle, mac_beacon, mac_operator, simulation_mode, weighing_mode,
    gross_weight, date_status, payload.
    """
    columns = [
        "published_at",
        "username",
        "server_profile",
        "event_type",
        "mac_vehicle",
        "mac_beacon",
        "mac_operator",
        "simulation_mode",
        "weighing_mode",
        "gross_weight",
        "date_status",
        "payload",
    ]
    values = [record.get(col) for col in columns]
    placeholders = ", ".join("?" for _ in columns)
    sql = (
        f"INSERT INTO event_log ({', '.join(columns)}) VALUES ({placeholders});"
    )
    async with aiosqlite.connect(_db_path) as db:
        cursor = await db.execute(sql, values)
        await db.commit()
        return cursor.lastrowid


async def insert_event_feed(record: dict) -> int:
    """Insert an event_feed row and return its new id.

    Expected keys: received_at, server_profile, event_id_field, mac_vehicle,
    mac_beacon, mac_operator, status, date_status, real_time, is_simulated,
    raw_payload.
    """
    columns = [
        "received_at",
        "server_profile",
        "event_id_field",
        "mac_vehicle",
        "mac_beacon",
        "mac_operator",
        "status",
        "date_status",
        "real_time",
        "is_simulated",
        "raw_payload",
    ]
    values = [record.get(col) for col in columns]
    placeholders = ", ".join("?" for _ in columns)
    sql = (
        f"INSERT INTO event_feed ({', '.join(columns)}) VALUES ({placeholders});"
    )
    async with aiosqlite.connect(_db_path) as db:
        cursor = await db.execute(sql, values)
        await db.commit()
        return cursor.lastrowid


async def upsert_user_last_seen(
    username: str, server_profile: str, ts: datetime
) -> None:
    """Insert or overwrite the last_seen timestamp for (username, profile)."""
    sql = """
        INSERT INTO user_last_seen (username, server_profile, last_seen)
        VALUES (?, ?, ?)
        ON CONFLICT(username, server_profile)
        DO UPDATE SET last_seen = excluded.last_seen;
    """
    async with aiosqlite.connect(_db_path) as db:
        await db.execute(sql, (username, server_profile, ts.isoformat()))
        await db.commit()


async def get_user_last_seen(
    username: str, server_profile: str
) -> datetime | None:
    """Return the stored last_seen timestamp, or None if no row exists."""
    sql = """
        SELECT last_seen FROM user_last_seen
        WHERE username = ? AND server_profile = ?;
    """
    async with aiosqlite.connect(_db_path) as db:
        cursor = await db.execute(sql, (username, server_profile))
        row = await cursor.fetchone()
    if row is None:
        return None
    return datetime.fromisoformat(row[0])


async def fetch_event_log(
    server_profile: str | None = None,
) -> list[dict]:
    """Return all event_log rows (optionally scoped to a profile) as dicts."""
    sql = "SELECT * FROM event_log"
    params: tuple = ()
    if server_profile is not None:
        sql += " WHERE server_profile = ?"
        params = (server_profile,)
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def fetch_event_feed(
    server_profile: str | None = None,
) -> list[dict]:
    """Return all event_feed rows (optionally scoped to a profile) as dicts."""
    sql = "SELECT * FROM event_feed"
    params: tuple = ()
    if server_profile is not None:
        sql += " WHERE server_profile = ?"
        params = (server_profile,)
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def find_recent_event_log_by_id(
    server_profile: str, event_guid: str, within_seconds: int = 5
) -> bool:
    """Return True if an event_log row for this profile has a payload whose Id
    matches event_guid within the recent window.

    Used by the Monitor to set the is_simulated flag. Matching is done on the
    payload JSON containing the Guid; the time window is applied to published_at.
    """
    from datetime import timezone, timedelta

    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=within_seconds)).isoformat()
    sql = """
        SELECT 1 FROM event_log
        WHERE server_profile = ?
          AND published_at >= ?
          AND payload LIKE ?
        LIMIT 1;
    """
    like = f'%{event_guid}%'
    async with aiosqlite.connect(_db_path) as db:
        cursor = await db.execute(sql, (server_profile, cutoff, like))
        row = await cursor.fetchone()
    return row is not None
