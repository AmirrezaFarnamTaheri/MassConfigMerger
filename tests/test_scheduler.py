import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from configstream.config import Settings
from configstream.scheduler import TestScheduler
from configstream.core.types import ConfigResult

@pytest.fixture
def test_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    return output_dir

@pytest.fixture
def mock_settings():
    """Fixture for mock Settings object."""
    return Settings()

@pytest.fixture
def mock_results():
    """Fixture for mock ConfigResult objects."""
    return [
        ConfigResult(
            config="vless://test",
            protocol="VLESS",
            ping_time=100.0,
            country="US",
            host="1.1.1.1",
            port=443,
            is_blocked=False,
            isp="Test Org",
            is_reachable=True,
        )
    ]

def test_scheduler_initialization(test_output_dir):
    """Test scheduler initialization."""
    settings = Settings()
    scheduler = TestScheduler(settings, test_output_dir)

    assert scheduler.output_dir == test_output_dir
    assert scheduler.current_results_file.parent == test_output_dir
    assert scheduler.history_file.parent == test_output_dir

@pytest.mark.asyncio
async def test_run_test_cycle(test_output_dir, mock_settings, mock_results):
    """Test running a single test cycle."""
    scheduler = TestScheduler(mock_settings, test_output_dir)

    with patch("configstream.scheduler.run_merger", new_callable=AsyncMock) as mock_run_merger:
        mock_run_merger.return_value = mock_results
        await scheduler.run_test_cycle()

        # Verify files were created
        assert scheduler.current_results_file.exists()
        assert scheduler.history_file.exists()

        # Verify JSON structure
        data = json.loads(scheduler.current_results_file.read_text())
        assert "timestamp" in data
        assert data["total_tested"] == 1
        assert data["successful"] == 1
        assert data["failed"] == 0
        assert "nodes" in data
        assert isinstance(data["nodes"], list)
        assert len(data["nodes"]) == 1

@pytest.mark.asyncio
async def test_multiple_cycles_history(test_output_dir, mock_settings, mock_results):
    """Test that history accumulates over multiple cycles."""
    scheduler = TestScheduler(mock_settings, test_output_dir)

    with patch("configstream.scheduler.run_merger", new_callable=AsyncMock) as mock_run_merger:
        mock_run_merger.return_value = mock_results

        # Run two test cycles
        await scheduler.run_test_cycle()
        await asyncio.sleep(0.01)
        await scheduler.run_test_cycle()

        # Read history file
        history_lines = scheduler.history_file.read_text().strip().split('\n')

        # Should have 2 entries
        assert len(history_lines) == 2

        # Each line should be valid JSON
        for line in history_lines:
            data = json.loads(line)
            assert "timestamp" in data