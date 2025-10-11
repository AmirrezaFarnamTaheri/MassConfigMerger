"""Integration test for the complete daemon system."""
import asyncio
import json
import time
import pytest
import requests
from pathlib import Path
from multiprocessing import Process
from configstream.cli import main as cli_main


def run_daemon_process(data_dir, port, sources_file):
    """Run daemon in separate process."""
    import sys

    sys.argv = [
        'configstream',
        'daemon',
        '--interval-hours', '1',
        '--web-port', str(port),
        '--sources', str(sources_file),
        '--data-dir', str(data_dir)
    ]
    cli_main()


@pytest.mark.integration
def test_full_daemon_workflow(tmp_path):
    """Test complete daemon workflow."""
    data_dir = tmp_path
    port = 8888

    # Create a dummy sources file for the test
    sources_file = data_dir / "sources.json"
    sources_file.write_text('["https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_base64.txt"]')

    print("\nStarting daemon integration test...")

    daemon_process = Process(
        target=run_daemon_process,
        args=(data_dir, port, sources_file)
    )
    daemon_process.start()

    try:
        # Wait for the initial test cycle to complete
        print("Waiting for daemon to start and run first test (up to 90s)...")
        time.sleep(90)

        # Check that the output files have been created in the correct data directory
        current_file = data_dir / "current_results.json"
        history_file = data_dir / "history.jsonl"

        assert current_file.exists(), f"current_results.json was not created in {data_dir}"
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