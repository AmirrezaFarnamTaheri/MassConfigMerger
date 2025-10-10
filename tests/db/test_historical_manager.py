import pytest
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import aiosqlite
from unittest.mock import patch

from configstream.db.historical_manager import HistoricalManager, NodeHistory

# Correct schema content
SCHEMA_CONTENT = """
CREATE TABLE IF NOT EXISTS node_tests (
    test_id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_hash TEXT NOT NULL,
    protocol TEXT,
    ip TEXT,
    port INTEGER,
    country_code TEXT,
    city TEXT,
    organization TEXT,
    ping_ms REAL,
    packet_loss_percent REAL,
    jitter_ms REAL,
    download_mbps REAL,
    upload_mbps REAL,
    is_blocked BOOLEAN,
    reputation_score INTEGER,
    cert_valid BOOLEAN,
    test_success BOOLEAN NOT NULL,
    error_message TEXT,
    test_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS node_reliability (
    config_hash TEXT PRIMARY KEY,
    total_tests INTEGER,
    successful_tests INTEGER,
    avg_ping_ms REAL,
    avg_packet_loss REAL,
    uptime_percent REAL,
    last_seen DATETIME,
    reliability_score REAL,
    first_seen DATETIME
);
"""


@pytest.fixture
async def manager(tmp_path) -> HistoricalManager:
    """Fixture for an initialized HistoricalManager using a real temp db."""
    db_path = tmp_path / "test_history.db"
    mgr = HistoricalManager(db_path)

    # Since the schema file doesn't exist, we patch the initialize method
    # to use our schema content directly. This avoids filesystem issues.
    with patch.object(Path, "exists", return_value=True), patch.object(
        Path, "read_text", return_value=SCHEMA_CONTENT
    ):
        await mgr.initialize()
    return mgr


def test_hash_config():
    """Test config hashing."""
    mgr = HistoricalManager(Path("/dummy.db"))
    config = "vless://test"
    # Correct SHA256 hash of "vless://test"
    expected_hash = "ebb4ca97d226d784ebae22d843cf5714c7d5d9baf5218fb092ee619ab4dc42cc"
    assert mgr.hash_config(config) == expected_hash


@pytest.mark.asyncio
async def test_initialize(manager: HistoricalManager):
    """Test database initialization."""
    assert manager.db_path.exists()
    async with aiosqlite.connect(manager.db_path) as db:
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in await cursor.fetchall()}
        assert "node_tests" in tables
        assert "node_reliability" in tables


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
        cursor = await db.execute("SELECT config_hash, ping_ms FROM node_tests")
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "hash1"
        assert row[1] == 100


@pytest.mark.asyncio
async def test_update_reliability(manager: HistoricalManager):
    """Test reliability score calculation and update."""
    config_hash = "hash_reliability"
    # Record a successful test
    await manager.record_test(
        {
            "config_hash": config_hash,
            "ping_ms": 100,
            "packet_loss_percent": 1,
            "test_success": True,
        }
    )
    # Record a failed test
    await manager.record_test({"config_hash": config_hash, "test_success": False})

    await manager.update_reliability(config_hash)

    async with aiosqlite.connect(manager.db_path) as db:
        cursor = await db.execute(
            "SELECT * FROM node_reliability WHERE config_hash = ?", (config_hash,)
        )
        row = await cursor.fetchone()
        assert row is not None
        # (config_hash, total_tests, successful_tests, avg_ping_ms, avg_packet_loss, uptime_percent, last_seen, reliability_score, first_seen)
        assert row[0] == config_hash
        assert row[1] == 2  # total_tests
        assert row[2] == 1  # successful_tests
        assert row[3] == 100.0  # avg_ping_ms
        assert row[4] == 1.0  # avg_packet_loss
        assert row[5] == 50.0  # uptime_percent
        # reliability = (50 * 0.5) + ((100 - 100/5) * 0.3) + ((100 - 1*10)*0.2)
        # reliability = 25 + (80 * 0.3) + (90 * 0.2) = 25 + 24 + 18 = 67
        assert round(row[7]) == 67


@pytest.mark.asyncio
async def test_get_reliable_nodes(manager: HistoricalManager):
    """Test retrieving reliable nodes."""
    now_ts = datetime.now()
    async with aiosqlite.connect(manager.db_path) as db:
        # High score, recent
        await db.execute(
            "INSERT INTO node_reliability VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("hash_good", 10, 9, 50, 0, 90.0, (now_ts - timedelta(days=1)).isoformat(), 95.0, now_ts.isoformat()),
        )
        # High score, old
        await db.execute(
            "INSERT INTO node_reliability VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("hash_old", 10, 9, 50, 0, 90.0, (now_ts - timedelta(days=10)).isoformat(), 95.0, now_ts.isoformat()),
        )
        # Low score, recent
        await db.execute(
            "INSERT INTO node_reliability VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("hash_bad", 10, 2, 500, 20, 20.0, (now_ts - timedelta(days=1)).isoformat(), 30.0, now_ts.isoformat()),
        )
        await db.commit()

    reliable_nodes = await manager.get_reliable_nodes(min_score=70)
    assert len(reliable_nodes) == 1
    node = reliable_nodes[0]
    assert node.config_hash == "hash_good"
    assert isinstance(node, NodeHistory)
    assert isinstance(node.last_seen, datetime)
    assert isinstance(node.first_seen, datetime)


@pytest.mark.asyncio
async def test_update_reliability_no_tests(manager: HistoricalManager):
    """Test reliability update for a node with no tests."""
    # This should not raise an error and not insert any row
    await manager.update_reliability("hash_no_tests")
    async with aiosqlite.connect(manager.db_path) as db:
        cursor = await db.execute(
            "SELECT * FROM node_reliability WHERE config_hash = ?", ("hash_no_tests",)
        )
        row = await cursor.fetchone()
        assert row is None