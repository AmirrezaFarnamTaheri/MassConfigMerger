from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from configstream.config import Settings
from configstream.scheduler import TestScheduler


@pytest.fixture
def settings() -> Settings:
    """Fixture for a Settings instance."""
    return Settings()


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Fixture for a temporary output directory."""
    return tmp_path


@pytest.fixture
def scheduler(settings: Settings, output_dir: Path) -> TestScheduler:
    """Fixture for a TestScheduler instance."""
    return TestScheduler(settings, output_dir)


@pytest.mark.asyncio
async def test_run_test_cycle(scheduler: TestScheduler, output_dir: Path):
    """Test the run_test_cycle method."""
    with patch("configstream.scheduler.run_merger", new_callable=AsyncMock) as mock_run_merger:
        # Mock the return value of run_merger
        mock_result = MagicMock()
        mock_result.ping_time = 0.1  # 100 ms
        mock_result.config = "test_config"
        mock_result.protocol = "test_protocol"
        mock_result.country = "US"
        mock_result.city = "Test City"
        mock_result.isp = "Test Org"
        mock_result.host = "1.1.1.1"
        mock_result.port = 1234
        mock_result.is_blocked = False
        mock_run_merger.return_value = [mock_result]

        # Run the test cycle
        await scheduler.run_test_cycle()

        # Check that the results were saved correctly
        current_results_file = output_dir / "current_results.json"
        history_file = output_dir / "history.jsonl"

        assert current_results_file.exists()
        assert history_file.exists()

        # Check the content of the current results file
        current_results = json.loads(current_results_file.read_text())
        assert current_results["total_tested"] == 1
        assert current_results["successful"] == 1
        assert current_results["nodes"][0]["protocol"] == "test_protocol"
        assert current_results["nodes"][0]["ping_ms"] == 100

        # Check the content of the history file
        history_content = history_file.read_text()
        history_data = json.loads(history_content)
        assert history_data["total_tested"] == 1


def test_start_and_stop(scheduler: TestScheduler):
    """Test the start and stop methods of the scheduler."""
    with patch("apscheduler.schedulers.asyncio.AsyncIOScheduler.add_job") as mock_add_job, \
         patch("apscheduler.schedulers.asyncio.AsyncIOScheduler.start") as mock_start, \
         patch("apscheduler.schedulers.asyncio.AsyncIOScheduler.shutdown") as mock_shutdown, \
         patch('apscheduler.schedulers.asyncio.AsyncIOScheduler.running', new_callable=PropertyMock) as mock_running:

        mock_running.return_value = False
        scheduler.start(interval_hours=1)
        mock_add_job.assert_called()
        mock_start.assert_called_once()

        mock_running.return_value = True
        scheduler.stop()
        mock_shutdown.assert_called_once()