"""Network quality testing (packet loss, jitter)."""
from __future__ import annotations

import asyncio
import statistics
import time
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class NetworkQualityResult:
    """Results from network quality tests."""
    packet_loss_percent: float
    jitter_ms: float
    avg_latency_ms: float
    samples: int

class NetworkQualityTester:
    """Tests packet loss and jitter."""

    def __init__(self, test_count: int = 20):
        self.test_count = test_count

    async def ping_once(self, host: str, port: int, timeout: float = 2.0) -> float:
        """Single ping test, returns latency in ms or -1 on failure."""
        start = time.time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()

            return (time.time() - start) * 1000

        except Exception:
            return -1.0

    async def test_quality(
        self,
        host: str,
        port: int,
        timeout: float = 2.0
    ) -> NetworkQualityResult:
        """Run multiple pings to measure quality."""
        latencies = []

        for _ in range(self.test_count):
            latency = await self.ping_once(host, port, timeout)
            latencies.append(latency)
            await asyncio.sleep(0.1)  # Small delay between pings

        # Calculate metrics
        successful = [l for l in latencies if l > 0]
        failed = len([l for l in latencies if l < 0])

        if not successful:
            return NetworkQualityResult(
                packet_loss_percent=100.0,
                jitter_ms=0.0,
                avg_latency_ms=0.0,
                samples=self.test_count
            )

        # Packet loss percentage
        packet_loss = (failed / self.test_count) * 100

        # Average latency
        avg_latency = statistics.mean(successful)

        # Jitter (standard deviation of latency)
        jitter = statistics.stdev(successful) if len(successful) > 1 else 0.0

        return NetworkQualityResult(
            packet_loss_percent=round(packet_loss, 2),
            jitter_ms=round(jitter, 2),
            avg_latency_ms=round(avg_latency, 2),
            samples=self.test_count
        )


# Convenience function
async def quick_quality_test(
    host: str,
    port: int,
    samples: int = 10
) -> NetworkQualityResult:
    """Quick network quality test with fewer samples.

    Args:
        host: Target hostname or IP
        port: Target port
        samples: Number of samples (default: 10)

    Returns:
        NetworkQualityResult with metrics
    """
    tester = NetworkQualityTester(test_count=samples)
    return await tester.test_quality(host, port)


# Convenience function
async def quick_quality_test(
    host: str,
    port: int,
    samples: int = 10
) -> NetworkQualityResult:
    """Quick network quality test with fewer samples.

    Args:
        host: Target hostname or IP
        port: Target port
        samples: Number of samples (default: 10)

    Returns:
        NetworkQualityResult with metrics
    """
    tester = NetworkQualityTester(test_count=samples)
    return await tester.test_quality(host, port)


# Convenience function
async def quick_quality_test(
    host: str,
    port: int,
    samples: int = 10
) -> NetworkQualityResult:
    """Quick network quality test with fewer samples.

    Args:
        host: Target hostname or IP
        port: Target port
        samples: Number of samples (default: 10)

    Returns:
        NetworkQualityResult with metrics
    """
    tester = NetworkQualityTester(test_count=samples)
    return await tester.test_quality(host, port)


# Convenience function
async def quick_quality_test(
    host: str,
    port: int,
    samples: int = 10
) -> NetworkQualityResult:
    """Quick network quality test with fewer samples.

    Args:
        host: Target hostname or IP
        port: Target port
        samples: Number of samples (default: 10)

    Returns:
        NetworkQualityResult with metrics
    """
    tester = NetworkQualityTester(test_count=samples)
    return await tester.test_quality(host, port)


# Convenience function
async def quick_quality_test(
    host: str,
    port: int,
    samples: int = 10
) -> NetworkQualityResult:
    """Quick network quality test with fewer samples.

    Args:
        host: Target hostname or IP
        port: Target port
        samples: Number of samples (default: 10)

    Returns:
        NetworkQualityResult with metrics
    """
    tester = NetworkQualityTester(test_count=samples)
    return await tester.test_quality(host, port)


# Convenience function
async def quick_quality_test(
    host: str,
    port: int,
    samples: int = 10
) -> NetworkQualityResult:
    """Quick network quality test with fewer samples.

    Args:
        host: Target hostname or IP
        port: Target port
        samples: Number of samples (default: 10)

    Returns:
        NetworkQualityResult with metrics
    """
    tester = NetworkQualityTester(test_count=samples)
    return await tester.test_quality(host, port)


# Convenience function
async def quick_quality_test(
    host: str,
    port: int,
    samples: int = 10
) -> NetworkQualityResult:
    """Quick network quality test with fewer samples.

    Args:
        host: Target hostname or IP
        port: Target port
        samples: Number of samples (default: 10)

    Returns:
        NetworkQualityResult with metrics
    """
    tester = NetworkQualityTester(test_count=samples)
    return await tester.test_quality(host, port)


# Convenience function
async def quick_quality_test(
    host: str,
    port: int,
    samples: int = 10
) -> NetworkQualityResult:
    """Quick network quality test with fewer samples.

    Args:
        host: Target hostname or IP
        port: Target port
        samples: Number of samples (default: 10)

    Returns:
        NetworkQualityResult with metrics
    """
    tester = NetworkQualityTester(test_count=samples)
    return await tester.test_quality(host, port)