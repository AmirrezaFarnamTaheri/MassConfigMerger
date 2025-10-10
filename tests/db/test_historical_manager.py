import pytest
from pathlib import Path
from configstream.db.historical_manager import HistoricalManager

@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture for a temporary database path."""
    return tmp_path / "test.db"

@pytest.mark.asyncio
async def test_initialize(db_path: Path):
    """Test database initialization."""
    manager = HistoricalManager(db_path)
    await manager.initialize()
    assert db_path.exists()

@pytest.mark.asyncio
async def test_record_and_get_history(db_path: Path):
    """Test recording and retrieving node history."""
    manager = HistoricalManager(db_path)
    await manager.initialize()

    config_hash = manager.hash_config("vless://test")
    test_data = {
        "config_hash": config_hash,
        "protocol": "VLESS",
        "ip": "1.1.1.1",
        "port": 443,
        "country_code": "US",
        "ping_ms": 100,
        "test_success": True,
    }

    await manager.record_test(test_data)
    history = await manager.get_node_history(config_hash)
    assert len(history) == 1
    assert history[0]["ping_ms"] == 100

@pytest.mark.asyncio
async def test_update_and_get_reliability(db_path: Path):
    """Test updating and retrieving reliability data."""
    manager = HistoricalManager(db_path)
    await manager.initialize()

    config_hash = manager.hash_config("vless://test")
    test_data_success = {
        "config_hash": config_hash,
        "ping_ms": 100,
        "test_success": True,
        "packet_loss_percent": 0,
        "jitter_ms": 10,
        "quality_score": 90,
    }
    test_data_failure = {
        "config_hash": config_hash,
        "ping_ms": -1,
        "test_success": False,
    }

    await manager.record_test(test_data_success)
    await manager.record_test(test_data_failure)
    await manager.record_test(test_data_success)
    await manager.update_reliability(config_hash)

    reliable_nodes = await manager.get_reliable_nodes(min_score=0)
    assert len(reliable_nodes) == 1
    node = reliable_nodes[0]
    assert node.total_tests == 3
    assert node.successful_tests == 2
    assert round(node.uptime_percent) == 67