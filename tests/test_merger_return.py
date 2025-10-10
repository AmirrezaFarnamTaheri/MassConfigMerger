"""Test that run_merger returns results correctly."""
import asyncio
import pytest
from configstream.config import Settings
from configstream.vpn_merger import run_merger


@pytest.mark.asyncio
async def test_run_merger_returns_list():
    """Test that run_merger returns a list."""
    settings = Settings()

    # Run the merger
    results = await run_merger(settings)

    # Verify it returns a list
    assert isinstance(results, list)
    print(f"✓ run_merger returned a list with {len(results)} items")


@pytest.mark.asyncio
async def test_run_merger_result_structure():
    """Test that results have the expected structure."""
    settings = Settings()
    results = await run_merger(settings)

    if len(results) > 0:
        # Check first result has expected attributes
        first_result = results[0]
        assert hasattr(first_result, 'raw_config')
        assert hasattr(first_result, 'protocol')
        assert hasattr(first_result, 'ping_ms')
        assert hasattr(first_result, 'ip')
        assert hasattr(first_result, 'port')
        print(f"✓ Results have correct structure")
        print(f"  Sample: {first_result.protocol} - {first_result.ip}:{first_result.port}")


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_run_merger_returns_list())
    asyncio.run(test_run_merger_result_structure())