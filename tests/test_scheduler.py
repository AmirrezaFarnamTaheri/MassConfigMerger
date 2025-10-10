"""Test the TestScheduler."""
import asyncio
import json
import pytest
from pathlib import Path
from configstream.config import Settings
from configstream.scheduler import TestScheduler


@pytest.fixture
def test_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    return output_dir


def test_scheduler_initialization(test_output_dir):
    """Test scheduler initialization."""
    settings = Settings()
    scheduler = TestScheduler(settings, test_output_dir)

    assert scheduler.output_dir == test_output_dir
    assert scheduler.current_results_file.parent == test_output_dir
    assert scheduler.history_file.parent == test_output_dir
    print("✓ Scheduler initialized correctly")


@pytest.mark.asyncio
async def test_run_test_cycle(test_output_dir):
    """Test running a single test cycle."""
    settings = Settings()
    scheduler = TestScheduler(settings, test_output_dir)

    # Run one test cycle
    await scheduler.run_test_cycle()

    # Verify files were created
    assert scheduler.current_results_file.exists()
    assert scheduler.history_file.exists()

    # Verify JSON structure
    data = json.loads(scheduler.current_results_file.read_text())
    assert "timestamp" in data
    assert "total_tested" in data
    assert "successful" in data
    assert "failed" in data
    assert "nodes" in data
    assert isinstance(data["nodes"], list)

    print(f"✓ Test cycle completed")
    print(f"  Total: {data['total_tested']}")
    print(f"  Successful: {data['successful']}")
    print(f"  Failed: {data['failed']}")


@pytest.mark.asyncio
async def test_multiple_cycles_history(test_output_dir):
    """Test that history accumulates over multiple cycles."""
    settings = Settings()
    scheduler = TestScheduler(settings, test_output_dir)

    # Run two test cycles
    await scheduler.run_test_cycle()
    await asyncio.sleep(0.5)  # Small delay
    await scheduler.run_test_cycle()

    # Read history file
    history_lines = scheduler.history_file.read_text().strip().split('\n')

    # Should have 2 entries
    assert len(history_lines) == 2

    # Each line should be valid JSON
    for line in history_lines:
        data = json.loads(line)
        assert "timestamp" in data

    print(f"✓ History tracking works")
    print(f"  Entries: {len(history_lines)}")


@pytest.mark.asyncio
async def test_run_test_cycle_exception(test_output_dir, monkeypatch):
    """Test that run_test_cycle handles exceptions gracefully."""
    settings = Settings()
    scheduler = TestScheduler(settings, test_output_dir)

    async def mock_run_merger_error(settings):
        raise ValueError("Test Exception")

    monkeypatch.setattr("configstream.vpn_merger.run_merger", mock_run_merger_error)

    await scheduler.run_test_cycle()
    # The test passes if no unhandled exception is raised.
    print("✓ Test cycle handles exceptions gracefully")


def test_scheduler_stop_not_running(test_output_dir):
    """Test stopping a scheduler that is not running."""
    settings = Settings()
    scheduler = TestScheduler(settings, test_output_dir)
    scheduler.stop()  # Should not raise an error
    assert not scheduler.scheduler.running
    print("✓ Stopping a non-running scheduler works as expected")


def test_get_next_run_time_no_job(test_output_dir):
    """Test get_next_run_time when no job is scheduled."""
    settings = Settings()
    scheduler = TestScheduler(settings, test_output_dir)
    assert scheduler.get_next_run_time() == "Not scheduled"
    print("✓ get_next_run_time returns 'Not scheduled' when no job is present")


def test_scheduler_start_and_get_next_run_time(test_output_dir):
    """Test starting the scheduler and getting the next run time."""
    settings = Settings()
    scheduler = TestScheduler(settings, test_output_dir)

    # Mock the test cycle to avoid running it
    scheduler.run_test_cycle = lambda: None

    scheduler.start(interval_hours=1)

    next_run_time_str = scheduler.get_next_run_time()
    assert next_run_time_str != "Not scheduled"

    # Check that the format is correct
    from datetime import datetime
    try:
        datetime.strptime(next_run_time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pytest.fail(f"get_next_run_time returned an invalid format: {next_run_time_str}")

    scheduler.stop()
    print("✓ Scheduler start and get_next_run_time work correctly")


if __name__ == "__main__":
    # Run tests
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        print("Test 1: Initialization")
        test_scheduler_initialization(test_dir / "test1")

        print("\nTest 2: Run test cycle")
        asyncio.run(test_run_test_cycle(test_dir / "test2"))

        print("\nTest 3: Multiple cycles")
        asyncio.run(test_multiple_cycles_history(test_dir / "test3"))