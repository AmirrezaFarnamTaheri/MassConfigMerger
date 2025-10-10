"""Integration test for the complete daemon system."""
import asyncio
import json
import time
import pytest
import requests
from pathlib import Path
from multiprocessing import Process
from configstream.cli import main as cli_main


def run_daemon_process(data_dir, port):
    """Run daemon in separate process."""
    import sys
    import asyncio
    sys.argv = [
        'configstream',
        'daemon',
        '--interval-hours', '1',
        '--web-port', str(port),
        '--data-dir', str(data_dir)
    ]
    asyncio.run(cli_main())


@pytest.mark.integration
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
    port = 8888  # Use non-standard port for testing

    print("\nStarting daemon integration test...")

    # Start daemon in subprocess
    daemon_process = Process(
        target=run_daemon_process,
        args=(data_dir, port)
    )
    daemon_process.start()

    try:
        # Wait for daemon to start and run first test
        print("Waiting for daemon to start and run first test (60s)...")
        time.sleep(60)

        # Check data files exist
        current_file = data_dir / "current_results.json"
        history_file = data_dir / "history.jsonl"

        assert current_file.exists(), "current_results.json not created"
        assert history_file.exists(), "history.jsonl not created"
        print("✓ Data files created")

        # Load and verify data
        data = json.loads(current_file.read_text())
        assert "timestamp" in data
        assert "nodes" in data
        assert isinstance(data["nodes"], list)
        print(f"✓ Current results valid ({len(data['nodes'])} nodes)")

        # Test web API
        base_url = f"http://localhost:{port}"

        # Test /api/current
        response = requests.get(f"{base_url}/api/current", timeout=5)
        assert response.status_code == 200
        api_data = response.json()
        assert "nodes" in api_data
        print("✓ /api/current endpoint works")

        # Test /api/statistics
        response = requests.get(f"{base_url}/api/statistics", timeout=5)
        assert response.status_code == 200
        stats = response.json()
        assert "total_nodes" in stats
        print("✓ /api/statistics endpoint works")

        # Test dashboard page
        response = requests.get(base_url, timeout=5)
        assert response.status_code == 200
        assert "ConfigStream Dashboard" in response.text
        print("✓ Dashboard page loads")

        print("\n✅ All integration tests passed!")

    finally:
        # Clean up
        print("\nStopping daemon...")
        daemon_process.terminate()
        daemon_process.join(timeout=5)
        if daemon_process.is_alive():
            daemon_process.kill()


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_full_daemon_workflow(Path(tmpdir))