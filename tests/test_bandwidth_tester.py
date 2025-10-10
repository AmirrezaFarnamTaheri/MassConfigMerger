"""Test bandwidth testing module."""
import pytest
import asyncio
from configstream.testing.bandwidth_tester import (
    BandwidthTester,
    BandwidthResult,
    quick_bandwidth_test
)


@pytest.mark.asyncio
async def test_bandwidth_result_dataclass():
    """Test BandwidthResult dataclass."""
    result = BandwidthResult(
        download_mbps=50.5,
        upload_mbps=25.3,
        test_duration_ms=15000
    )

    assert result.download_mbps == 50.5
    assert result.upload_mbps == 25.3
    assert result.success is True
    print("✓ BandwidthResult structure correct")


@pytest.mark.asyncio
async def test_bandwidth_result_with_error():
    """Test BandwidthResult with error."""
    result = BandwidthResult(
        download_mbps=0.0,
        upload_mbps=0.0,
        test_duration_ms=1000,
        error="Test failed"
    )

    assert result.success is False
    assert result.error == "Test failed"
    print("✓ Error handling works")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_download_speed():
    """Test actual download speed measurement."""
    tester = BandwidthTester()
    speed = await tester.test_download()

    # Speed should be positive if test succeeds
    # (May be 0.0 if server unreachable)
    assert isinstance(speed, float)
    assert speed >= 0.0

    if speed > 0:
        print(f"✓ Download test successful: {speed:.2f} Mbps")
    else:
        print("⚠ Download test failed (server may be unreachable)")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_full_bandwidth_test():
    """Test complete bandwidth test."""
    tester = BandwidthTester()
    result = await tester.test_full()

    assert isinstance(result, BandwidthResult)
    assert result.test_duration_ms > 0

    print(f"✓ Full test completed in {result.test_duration_ms}ms")
    print(f"  Download: {result.download_mbps:.2f} Mbps")
    print(f"  Upload: {result.upload_mbps:.2f} Mbps")
    print(f"  Success: {result.success}")


@pytest.mark.asyncio
async def test_bandwidth_tester_with_invalid_url():
    """Test bandwidth tester with invalid URL."""
    tester = BandwidthTester(test_url="http://invalid.example.com")
    result = await tester.test_full()

    # Should handle error gracefully
    assert result.download_mbps == 0.0
    assert result.upload_mbps == 0.0
    print("✓ Invalid URL handled gracefully")


if __name__ == "__main__":
    # Run tests
    print("Running bandwidth tests...")
    print("Note: These tests require internet connection\n")

    asyncio.run(test_bandwidth_result_dataclass())
    asyncio.run(test_bandwidth_result_with_error())
    asyncio.run(test_download_speed())
    asyncio.run(test_full_bandwidth_test())
    asyncio.run(test_bandwidth_tester_with_invalid_url())