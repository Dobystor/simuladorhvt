"""Integration tests for the SQLite database layer.

Requirements: 13.4
"""

from datetime import datetime, timezone

import aiosqlite
import pytest

from app import database


@pytest.fixture
def db_file(tmp_path):
    path = str(tmp_path / "test.sqlite")
    database.configure_db_path(path)
    return path


async def _table_names(path):
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        )
        rows = await cursor.fetchall()
    return {r[0] for r in rows}


async def _index_names(path):
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';"
        )
        rows = await cursor.fetchall()
    return {r[0] for r in rows}


async def test_init_creates_all_tables(db_file):
    await database.init_db(db_file)
    tables = await _table_names(db_file)
    assert {"schema_version", "event_log", "event_feed", "user_last_seen"} <= tables


async def test_init_creates_all_indexes(db_file):
    await database.init_db(db_file)
    indexes = await _index_names(db_file)
    expected = {
        "idx_log_profile",
        "idx_log_vehicle",
        "idx_log_published",
        "idx_log_username",
        "idx_log_type",
        "idx_feed_received",
        "idx_feed_profile",
        "idx_feed_vehicle",
    }
    assert expected <= indexes


async def test_init_is_idempotent(db_file):
    await database.init_db(db_file)
    await database.init_db(db_file)  # must not raise
    tables = await _table_names(db_file)
    assert "event_log" in tables
    # schema_version has exactly one row
    async with aiosqlite.connect(db_file) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM schema_version;")
        (count,) = await cursor.fetchone()
    assert count == 1


async def test_insert_and_fetch_event_log(db_file):
    await database.init_db(db_file)
    new_id = await database.insert_event_log(
        {
            "published_at": "2026-01-01T00:00:00+00:00",
            "username": "alice",
            "server_profile": "Local",
            "event_type": "Load",
            "mac_vehicle": "AA:BB",
            "payload": "{}",
        }
    )
    assert new_id == 1
    rows = await database.fetch_event_log()
    assert len(rows) == 1
    assert rows[0]["username"] == "alice"
    assert rows[0]["event_type"] == "Load"


async def test_insert_and_fetch_event_feed(db_file):
    await database.init_db(db_file)
    await database.insert_event_feed(
        {
            "received_at": "2026-01-01T00:00:00+00:00",
            "server_profile": "Local",
            "mac_vehicle": "AA:BB",
            "status": 1,
            "is_simulated": 1,
            "raw_payload": "{}",
        }
    )
    rows = await database.fetch_event_feed()
    assert len(rows) == 1
    assert rows[0]["is_simulated"] == 1


async def test_upsert_and_get_user_last_seen(db_file):
    await database.init_db(db_file)
    assert await database.get_user_last_seen("alice", "Local") is None

    ts1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await database.upsert_user_last_seen("alice", "Local", ts1)
    assert await database.get_user_last_seen("alice", "Local") == ts1

    ts2 = datetime(2026, 2, 1, tzinfo=timezone.utc)
    await database.upsert_user_last_seen("alice", "Local", ts2)
    assert await database.get_user_last_seen("alice", "Local") == ts2  # overwritten


async def test_find_recent_event_log_by_id(db_file):
    await database.init_db(db_file)
    guid = "11111111-2222-3333-4444-555555555555"
    now = datetime.now(timezone.utc).isoformat()
    await database.insert_event_log(
        {
            "published_at": now,
            "username": "alice",
            "server_profile": "Local",
            "event_type": "Load",
            "payload": f'{{"Id": "{guid}"}}',
        }
    )
    assert await database.find_recent_event_log_by_id("Local", guid) is True
    assert await database.find_recent_event_log_by_id("Local", "no-match") is False
