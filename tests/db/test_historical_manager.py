import pytest
import asyncio
import aiosqlite
from pathlib import Path
from datetime import datetime, timedelta
from configstream.db.historical_manager import HistoricalManager, NodeHistory

@pytest.fixture
async def db_manager(tmp_path):
    """Fixture to create a HistoricalManager with a temporary db."""
    db_path = tmp_path / "test_history.db"
    manager = HistoricalManager(db_path)
    await manager.initialize()
    return manager

@pytest.mark.asyncio
async def test_initialization(db_manager: HistoricalManager):
    """Test that the database is initialized correctly."""
    assert db_manager.db_path.exists()
    async with aiosqlite.connect(db_manager.db_path) as db:
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in await cursor.fetchall()]
        assert "node_test_history" in tables
        assert "node_reliability" in tables
        assert "performance_summary" in tables

@pytest.mark.asyncio
async def test_record_and_retrieve_test(db_manager: HistoricalManager):
    """Test recording a test and retrieving it."""
    config = "test_config"
    config_hash = db_manager.hash_config(config)
    test_data = {
        "config_hash": config_hash,
        "protocol": "test",
        "ip": "1.1.1.1",
        "port": 1234,
        "ping_ms": 100,
        "test_success": True,
    }
    await db_manager.record_test(test_data)

    history = await db_manager.get_node_history(config_hash)
    assert len(history) == 1
    assert history[0]["ping_ms"] == 100

@pytest.mark.asyncio
async def test_update_reliability(db_manager: HistoricalManager):
    """Test the reliability metrics are updated correctly."""
    config = "test_config_2"
    config_hash = db_manager.hash_config(config)

    # Record two successful tests
    await db_manager.record_test({
        "config_hash": config_hash, "protocol": "test", "ip": "2.2.2.2", "port": 5678,
        "ping_ms": 50, "test_success": True, "quality_score": 90
    })
    await db_manager.record_test({
        "config_hash": config_hash, "protocol": "test", "ip": "2.2.2.2", "port": 5678,
        "ping_ms": 150, "test_success": True, "quality_score": 70
    })

    # Record a failed test
    await db_manager.record_test({
        "config_hash": config_hash, "protocol": "test", "ip": "2.2.2.2", "port": 5678,
        "ping_ms": -1, "test_success": False, "quality_score": 0
    })

    await db_manager.update_reliability(config_hash)

    reliable_nodes = await db_manager.get_reliable_nodes(min_score=0)
    assert len(reliable_nodes) == 1
    node = reliable_nodes[0]

    assert node.total_tests == 3
    assert node.successful_tests == 2
    assert node.failed_tests == 1
    assert node.avg_ping_ms == 100  # (50 + 150) / 2
    assert node.uptime_percent == pytest.approx((2/3) * 100)
    assert node.reliability_score > 0

@pytest.mark.asyncio
async def test_get_reliable_nodes(db_manager: HistoricalManager):
    """Test retrieving reliable nodes based on score and activity."""
    # Add a reliable node
    reliable_hash = db_manager.hash_config("reliable")
    for _ in range(5):
        await db_manager.record_test({"config_hash": reliable_hash, "test_success": True, "ping_ms": 50, "quality_score": 95})
    await db_manager.update_reliability(reliable_hash)

    # Add an unreliable node
    unreliable_hash = db_manager.hash_config("unreliable")
    for _ in range(5):
        await db_manager.record_test({"config_hash": unreliable_hash, "test_success": False, "ping_ms": -1, "quality_score": 0})
    await db_manager.update_reliability(unreliable_hash)

    # Test with default high score
    nodes = await db_manager.get_reliable_nodes()
    assert len(nodes) == 1
    assert nodes[0].config_hash == reliable_hash

    # Test with low score to get both
    nodes = await db_manager.get_reliable_nodes(min_score=10)
    assert len(nodes) == 2

    # Test days_active
    # Manually update last_seen to be old
    async with aiosqlite.connect(db_manager.db_path) as db:
        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        await db.execute("UPDATE node_reliability SET last_seen = ? WHERE config_hash = ?", (old_date, reliable_hash))
        await db.commit()

    nodes = await db_manager.get_reliable_nodes(days_active=7, min_score=10)
    assert len(nodes) == 1 # Only the unreliable one is recent enough
    assert nodes[0].config_hash == unreliable_hash