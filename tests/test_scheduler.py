import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, PropertyMock

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


def test_scheduler_initialization(test_output_dir):
    """Test scheduler initialization."""
    settings = Settings()
    scheduler = TestScheduler(settings, test_output_dir)

    assert scheduler.output_dir == test_output_dir
    assert scheduler.current_results_file.parent == test_output_dir
    assert scheduler.history_file.parent == test_output_dir

@pytest.mark.asyncio
async def test_run_test_cycle(test_output_dir, mock_settings, config_result):
    """Test running a single test cycle."""
    scheduler = TestScheduler(mock_settings, test_output_dir)

    with patch("configstream.vpn_merger.run_merger", new_callable=AsyncMock) as mock_run_merger:
        mock_run_merger.return_value = [config_result]
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
async def test_multiple_cycles_history(test_output_dir, mock_settings, config_result):
    """Test that history accumulates over multiple cycles."""
    scheduler = TestScheduler(mock_settings, test_output_dir)

    with patch("configstream.vpn_merger.run_merger", new_callable=AsyncMock) as mock_run_merger:
        mock_run_merger.return_value = [config_result]

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

@pytest.mark.asyncio
async def test_run_advanced_tests(test_output_dir, mock_settings, config_result):
    """Test that advanced tests are run when enabled."""
    mock_settings.testing.enable_advanced_tests = True
    scheduler = TestScheduler(mock_settings, test_output_dir)

    with patch("configstream.vpn_merger.run_merger", new_callable=AsyncMock) as mock_run_merger, \
         patch("configstream.scheduler.TestScheduler.run_advanced_tests_on_top_nodes", new_callable=AsyncMock) as mock_run_advanced_tests:
        mock_run_merger.return_value = [config_result]
        mock_run_advanced_tests.return_value = [config_result]

        await scheduler.run_test_cycle()

        mock_run_advanced_tests.assert_awaited_once_with([config_result])

def test_stop_scheduler(test_output_dir, mock_settings):
    """Test that the scheduler can be stopped."""
    scheduler = TestScheduler(mock_settings, test_output_dir)
    with patch("apscheduler.schedulers.background.BackgroundScheduler.shutdown") as mock_shutdown:
        scheduler.stop()
        mock_shutdown.assert_not_called()

        with patch('apscheduler.schedulers.base.BaseScheduler.running', new_callable=PropertyMock, return_value=True):
            scheduler.stop()

        mock_shutdown.assert_called_once()