"""
Component integration test for the Scheduler and Web Dashboard.

This test verifies that the TestScheduler correctly produces a results file
and that the web dashboard can correctly read and serve that data.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

# Import the components to be tested
from configstream.scheduler import TestScheduler
from configstream.web_dashboard import app
from configstream.config import Settings
from configstream.core.types import ConfigResult


@pytest.mark.asyncio
async def test_scheduler_to_dashboard_pipeline(tmp_path):
    """
    Tests the data pipeline from the scheduler writing a file to the
    dashboard reading and serving it.
    """
    # 1. Setup the environment
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()

    settings = Settings()
    # Point the settings to our temporary directory
    settings.sources.sources_file = str(tmp_path / "sources.txt")

    # Create a test client for the Flask app
    app.config['TESTING'] = True
    client = app.test_client()

    # 2. Define the mock results for the merger
    mock_results = [
        ConfigResult(
            config="vmess://mock-config-string",
            protocol="vmess",
            is_reachable=True,
            ping_time=0.123,  # in seconds
            country="US",
            host="1.2.3.4",
            port=443,
            isp="Test ISP",
            is_blocked=False,
        )
    ]

    # 3. Create an async mock function to replace run_merger
    async def mock_run_merger(*args, **kwargs):
        return mock_results

    # 4. Patch `run_merger` where it's used (in the scheduler)
    with patch("configstream.scheduler.run_merger", new=mock_run_merger):
        # Instantiate the scheduler, pointing it to our temp data directory
        scheduler = TestScheduler(settings, data_dir)

        # 5. Manually trigger a test cycle
        await scheduler.run_test_cycle()

        # 6. Verify the scheduler's output
        results_file = data_dir / "current_results.json"
        assert results_file.exists(), "Scheduler did not create the results file."

        file_data = json.loads(results_file.read_text())
        assert file_data["successful"] == 1
        assert file_data["nodes"][0]["ping_ms"] == 123  # Verify time->ms conversion

        # 7. Verify the web dashboard can read and serve the file

        # Point the dashboard's data manager to the same temp directory
        from configstream.web_dashboard import dashboard_data
        dashboard_data.data_dir = data_dir
        dashboard_data.current_file = results_file

        response = client.get("/api/current")
        assert response.status_code == 200

        api_data = response.get_json()
        assert len(api_data["nodes"]) == 1
        assert api_data["nodes"][0]["ping_ms"] == 123
        assert api_data["nodes"][0]["protocol"] == "vmess"
        assert api_data["nodes"][0]["organization"] == "Test ISP"