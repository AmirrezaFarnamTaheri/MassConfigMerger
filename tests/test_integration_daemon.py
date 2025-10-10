"""Integration test for the complete daemon system."""
import asyncio
import json
import time
import pytest
import requests
from pathlib import Path
from multiprocessing import Process, set_start_method
from configstream.cli import main as cli_main

# Set start method to 'fork' to avoid issues with multiprocessing in pytest
try:
    set_start_method("fork")
except RuntimeError:
    pass

def run_daemon_process(data_dir, port):
    """Run daemon in separate process."""
    import sys
    sys.argv = [
        'configstream',
        'daemon',
        '--interval-hours', '1',
        '--data-dir', str(data_dir),
        '--web-port', str(port)
    ]
    cli_main()

@pytest.mark.integration
@pytest.mark.slow
def test_full_daemon_workflow(tmp_path):
    """Test complete daemon workflow.

    This test:
    1. Starts the daemon
    2. Waits for initial test cycle
    3. Verifies data files are created
    4. Tests web API endpoints
    5. Shuts down gracefully
    """
    data_dir = tmp_path / "daemon_test"
    data_dir.mkdir()
    port = 8888

    daemon_process = Process(target=run_daemon_process, args=(data_dir, port))
    daemon_process.start()

    try:
        # Wait for the initial test cycle to complete by polling for the results file
        current_file = data_dir / "current_results.json"
        history_file = data_dir / "history.jsonl"

        print("Waiting for daemon to create results file (up to 60s)...")
        for _ in range(60):
            if current_file.exists() and history_file.exists():
                break
            time.sleep(1)

        assert current_file.exists(), "current_results.json was not created after 60 seconds"
        assert history_file.exists(), "history.jsonl was not created after 60 seconds"

        # Load and verify data
        data = json.loads(current_file.read_text())
        assert "timestamp" in data
        assert "nodes" in data
        assert isinstance(data["nodes"], list)

        # Test web API
        base_url = f"http://localhost:{port}"

        response = requests.get(f"{base_url}/api/current", timeout=10)
        assert response.status_code == 200
        api_data = response.json()
        assert "nodes" in api_data

        response = requests.get(f"{base_url}/api/statistics", timeout=10)
        assert response.status_code == 200
        stats = response.json()
        assert "total_nodes" in stats

        response = requests.get(base_url, timeout=10)
        assert response.status_code == 200
        assert "ConfigStream Dashboard" in response.text

    finally:
        # Clean up
        daemon_process.terminate()
        daemon_process.join(timeout=5)
        if daemon_process.is_alive():
            daemon_process.kill()