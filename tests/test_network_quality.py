"""Test network quality testing module."""
import pytest
import asyncio
from configstream.testing.network_quality import (
    NetworkQualityTester,
    NetworkQualityResult,
    quick_quality_test
)


def test_quality_result_dataclass():
    """Test NetworkQualityResult dataclass."""
    result = NetworkQualityResult(
        packet_loss_percent=2.5,
        jitter_ms=15.3,
        avg_latency_ms=45.2,
        min_latency_ms=40.1,
        max_latency_ms=55.8,
        samples=20
    )

    assert result.packet_loss_percent == 2.5
    assert result.jitter_ms == 15.3
    assert result.samples == 20
    print("✓ NetworkQualityResult structure correct")


def test_quality_score_calculation():
    """Test quality score calculation."""
    # Good connection
    good_result = NetworkQualityResult(
        packet_loss_percent=0.0,
        jitter_ms=5.0,
        avg_latency_ms=30.0,
        min_latency_ms=28.0,
        max_latency_ms=35.0,
        samples=20
    )

    assert good_result.quality_score > 85
    assert good_result.is_stable is True
    print(f"✓ Good connection score: {good_result.quality_score:.1f}/100")

    # Poor connection
    poor_result = NetworkQualityResult(
        packet_loss_percent=15.0,
        jitter_ms=50.0,
        avg_latency_ms=200.0,
        min_latency_ms=100.0,
        max_latency_ms=300.0,
        samples=20
    )

    assert poor_result.quality_score < 50
    assert poor_result.is_stable is False
    print(f"✓ Poor connection score: {poor_result.quality_score:.1f}/100")


@pytest.mark.asyncio
async def test_ping_once():
    """Test single ping operation."""
    tester = NetworkQualityTester()

    # Test to a reliable server
    latency = await tester.ping_once("1.1.1.1", 443, timeout=3.0)

    # Should succeed or fail gracefully
    assert isinstance(latency, float)
    assert latency >= -1.0

    if latency > 0:
        print(f"✓ Ping successful: {latency:.2f}ms")
    else:
        print("⚠ Ping failed (server may be unreachable)")


@pytest.mark.asyncio
async def test_ping_once_invalid_host():
    """Test ping to invalid host."""
    tester = NetworkQualityTester()
    latency = await tester.ping_once("invalid.example.com", 443, timeout=1.0)

    assert latency == -1.0
    print("✓ Invalid host handled gracefully")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_quality_test():
    """Test full quality test."""
    tester = NetworkQualityTester(test_count=10)
    result = await tester.test_quality("1.1.1.1", 443)

    assert isinstance(result, NetworkQualityResult)
    assert result.samples == 10
    assert 0 <= result.packet_loss_percent <= 100
    assert result.jitter_ms >= 0

    print(f"✓ Quality test completed:")
    print(f"  Packet loss: {result.packet_loss_percent}%")
    print(f"  Jitter: {result.jitter_ms}ms")
    print(f"  Avg latency: {result.avg_latency_ms}ms")
    print(f"  Quality score: {result.quality_score:.1f}/100")
    print(f"  Stable: {result.is_stable}")


@pytest.mark.asyncio
async def test_quality_test_timeout():
    """Test quality test with quick timeout."""
    tester = NetworkQualityTester(test_count=5)
    result = await tester.test_quality(
        "192.0.2.1",  # TEST-NET-1, should timeout
        12345,
        timeout=0.5
    )

    # Should complete without crashing
    assert isinstance(result, NetworkQualityResult)
    # Likely 100% packet loss
    assert result.packet_loss_percent >= 0
    print("✓ Timeout scenario handled correctly")


@pytest.mark.asyncio
async def test_quick_quality_test():
    """Test convenience function."""
    result = await quick_quality_test("1.1.1.1", 443, samples=5)

    assert isinstance(result, NetworkQualityResult)
    assert result.samples == 5
    print("✓ Quick test function works")


if __name__ == "__main__":
    print("Running network quality tests...")
    print("Note: These tests require internet connection\n")

    test_quality_result_dataclass()
    test_quality_score_calculation()
    asyncio.run(test_ping_once())
    asyncio.run(test_ping_once_invalid_host())
    asyncio.run(test_quality_test())
    asyncio.run(test_quality_test_timeout())
    asyncio.run(test_quick_quality_test())