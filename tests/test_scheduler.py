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