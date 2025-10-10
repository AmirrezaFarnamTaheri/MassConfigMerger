"""Tests for the HistoricalManager."""
import pytest
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import aiosqlite

from configstream.db.historical_manager import HistoricalManager, NodeHistory


@pytest.fixture
async def manager(tmp_path: Path) -> HistoricalManager:
    """Fixture to create and initialize a HistoricalManager instance."""
    db_path = tmp_path / "test_history.db"
    manager = HistoricalManager(db_path)
    await manager.initialize()
    return manager


@pytest.mark.asyncio
async def test_initialization(manager: HistoricalManager):
    """Test that the database and tables are created."""
    assert manager.db_path.exists()
    async with aiosqlite.connect(manager.db_path) as db:
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='node_test_history'")
        assert await cursor.fetchone() is not None
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='node_reliability'")
        assert await cursor.fetchone() is not None


@pytest.mark.asyncio
async def test_record_test(manager: HistoricalManager):
    """Test recording a single test result."""
    test_data = {
        "config_hash": "hash1",
        "protocol": "vless",
        "ping_ms": 100,
        "test_success": True,
    }
    await manager.record_test(test_data)

    async with aiosqlite.connect(manager.db_path) as db:
        cursor = await db.execute("SELECT * FROM node_test_history WHERE config_hash = ?", ("hash1",))
        row = await cursor.fetchone()
        assert row is not None
        assert row[1] == "hash1"
        # Correct index for ping_ms is 9 (id is 0)
        assert row[9] == 100


@pytest.mark.asyncio
async def test_update_reliability(manager: HistoricalManager):
    """Test reliability score calculation and update."""
    config_hash = "hash_reliability"
    await manager.record_test(
        {
            "config_hash": config_hash,
            "ping_ms": 100,
            "quality_score": 80,
            "test_success": True,
        }
    )
    await manager.record_test({"config_hash": config_hash, "test_success": False})

    await manager.update_reliability(config_hash)

    async with aiosqlite.connect(manager.db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM node_reliability WHERE config_hash = ?", (config_hash,))
        row = await cursor.fetchone()
        assert row is not None
        assert row["total_tests"] == 2
        assert row["successful_tests"] == 1
        assert row["uptime_percent"] == 50.0
        assert row["avg_ping_ms"] == 100.0


@pytest.mark.asyncio
async def test_get_reliable_nodes(manager: HistoricalManager):
    """Test retrieving reliable nodes."""
    now_ts = datetime.now()
    now_iso = now_ts.isoformat()
    async with aiosqlite.connect(manager.db_path) as db:
        # Provide all required fields for the INSERT
        await db.execute(
            """INSERT INTO node_reliability (config_hash, total_tests, successful_tests, failed_tests, reliability_score, last_seen, first_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("hash_good", 10, 9, 1, 95.0, (now_ts - timedelta(days=1)).isoformat(), now_iso),
        )
        await db.execute(
            """INSERT INTO node_reliability (config_hash, total_tests, successful_tests, failed_tests, reliability_score, last_seen, first_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("hash_old", 10, 9, 1, 95.0, (now_ts - timedelta(days=10)).isoformat(), now_iso),
        )
        await db.execute(
            """INSERT INTO node_reliability (config_hash, total_tests, successful_tests, failed_tests, reliability_score, last_seen, first_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("hash_bad", 10, 2, 8, 30.0, (now_ts - timedelta(days=1)).isoformat(), now_iso),
        )
        await db.commit()

    reliable_nodes = await manager.get_reliable_nodes(min_score=70)
    assert len(reliable_nodes) == 1
    assert reliable_nodes[0].config_hash == "hash_good"


@pytest.mark.asyncio
async def test_update_reliability_no_tests(manager: HistoricalManager):
    """Test reliability update for a node with no tests."""
    await manager.update_reliability("hash_no_tests")
    async with aiosqlite.connect(manager.db_path) as db:
        cursor = await db.execute("SELECT * FROM node_reliability WHERE config_hash = ?", ("hash_no_tests",))
        row = await cursor.fetchone()
        assert row is None