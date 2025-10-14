import pytest
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from pathlib import Path
import json
from datetime import datetime

from configstream.scheduler import TestScheduler
TestScheduler.__test__ = False
from configstream.config import Settings
from configstream.core.config_processor import ConfigResult


@pytest.fixture
def mock_settings():
    """Fixture for mock Settings object."""
    return Settings()


@pytest.mark.asyncio
async def test_scheduler_run_test_cycle(mock_settings, tmp_path):
    """Test a single run of the test cycle."""
    output_dir = tmp_path
    scheduler = TestScheduler(settings=mock_settings, output_dir=output_dir)

    mock_results = [
        ConfigResult(
            config="vless://test",
            protocol="VLESS",
            ping_time=100,
            country="US",
            is_reachable=True,
        )
    ]

    with patch(
        "configstream.scheduler.run_merger", new_callable=AsyncMock
    ) as mock_run_merger:
        mock_run_merger.return_value = mock_results
        await scheduler.run_test_cycle()

        # Check that current_results.json was written correctly
        current_results_path = output_dir / "current_results.json"
        assert current_results_path.exists()
        data = json.loads(current_results_path.read_text())
        assert data["successful"] == 1
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["protocol"] == "VLESS"

        # Check that history.jsonl was appended
        history_file = output_dir / "history.jsonl"
        assert history_file.exists()
        history_data = json.loads(history_file.read_text())
        assert history_data["total_tested"] == 1


@pytest.mark.asyncio
async def test_scheduler_run_test_cycle_exception(mock_settings, tmp_path):
    """Test that the test cycle handles exceptions gracefully."""
    output_dir = tmp_path
    scheduler = TestScheduler(settings=mock_settings, output_dir=output_dir)

    with patch(
        "configstream.scheduler.run_merger", new_callable=AsyncMock
    ) as mock_run_merger:
        mock_run_merger.side_effect = Exception("Test error")
        # This should not raise an exception
        await scheduler.run_test_cycle()

        # Verify that no files were written
        assert not (output_dir / "current_results.json").exists()
        assert not (output_dir / "history.jsonl").exists()


def test_scheduler_start_and_stop(mock_settings, tmp_path):
    """Test the start and stop methods of the scheduler."""
    scheduler = TestScheduler(settings=mock_settings, output_dir=tmp_path)

    with patch.object(scheduler.scheduler, "add_job") as mock_add_job, \
         patch.object(scheduler.scheduler, "start") as mock_start, \
         patch.object(scheduler.scheduler, "shutdown") as mock_shutdown:

        scheduler.start(interval_hours=5)

        # Verify that jobs were added for the interval and initial run
        assert mock_add_job.call_count == 1
        mock_start.assert_called_once()

        # Simulate the scheduler running
        with patch('apscheduler.schedulers.base.BaseScheduler.running', new_callable=PropertyMock) as mock_running:
            mock_running.return_value = True
            scheduler.stop()
            mock_shutdown.assert_called_once()
