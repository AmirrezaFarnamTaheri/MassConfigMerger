# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""Network quality testing for packet loss and jitter measurement.

This module provides tools to measure network stability beyond simple
latency tests.
"""
from __future__ import annotations

import asyncio
import logging
import statistics
import time
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class NetworkQualityResult:
    """Results from network quality tests.

    Attributes:
        packet_loss_percent: Percentage of packets lost (0-100)
        jitter_ms: Variation in latency (standard deviation)
        avg_latency_ms: Average latency across all samples
        min_latency_ms: Minimum latency observed
        max_latency_ms: Maximum latency observed
        samples: Number of test samples taken
    """
    packet_loss_percent: float
    jitter_ms: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    samples: int

    @property
    def quality_score(self) -> float:
        """Calculate overall quality score (0-100).

        Higher is better. Based on:
        - Packet loss (40% weight)
        - Jitter (30% weight)
        - Average latency (30% weight)
        """
        # Packet loss score (100 - loss%)
        loss_score = max(0, 100 - self.packet_loss_percent)

        # Jitter score (lower jitter = higher score)
        # Good: <10ms, Acceptable: <30ms, Poor: >30ms
        jitter_score = max(0, 100 - (self.jitter_ms * 2))

        # Latency score
        # Good: <50ms, Acceptable: <150ms, Poor: >150ms
        latency_score = max(0, 100 - (self.avg_latency_ms / 2))

        return (
            loss_score * 0.4 +
            jitter_score * 0.3 +
            latency_score * 0.3
        )

    @property
    def is_stable(self) -> bool:
        """Check if connection is stable enough for real-time apps.

        Criteria for stability:
        - Packet loss < 5%
        - Jitter < 30ms
        - Avg latency < 150ms
        """
        return (
            self.packet_loss_percent < 5.0 and
            self.jitter_ms < 30.0 and
            self.avg_latency_ms < 150.0
        )


class NetworkQualityTester:
    """Tests packet loss and jitter through multiple ping samples.

    This class performs multiple connection attempts to a target host
    and analyzes the results to determine network stability.

    Example:
        >>> tester = NetworkQualityTester(test_count=20)
        >>> result = await tester.test_quality("example.com", 443)
        >>> print(f"Quality score: {result.quality_score:.1f}/100")
    """

    def __init__(self, test_count: int = 20):
        """Initialize quality tester.

        Args:
            test_count: Number of ping samples to collect (default: 20)
        """
        self.test_count = test_count

    async def ping_once(
        self,
        host: str,
        port: int,
        timeout: float = 2.0
    ) -> float:
        """Single ping test to measure latency.

        Args:
            host: Target hostname or IP
            port: Target port
            timeout: Timeout in seconds

        Returns:
            Latency in milliseconds, or -1.0 on failure
        """
        start = time.time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )

            # Close connection immediately
            writer.close()
            await writer.wait_closed()

            latency_ms = (time.time() - start) * 1000
            return latency_ms

        except asyncio.TimeoutError:
            logger.debug(f"Ping timeout to {host}:{port}")
            return -1.0
        except Exception as e:
            logger.debug(f"Ping failed to {host}:{port}: {e}")
            return -1.0

    async def test_quality(
        self,
        host: str,
        port: int,
        timeout: float = 2.0,
        interval: float = 0.1
    ) -> NetworkQualityResult:
        """Run multiple pings to measure network quality.

        Args:
            host: Target hostname or IP
            port: Target port
            timeout: Timeout per ping in seconds
            interval: Delay between pings in seconds

        Returns:
            NetworkQualityResult with all metrics
        """
        logger.info(
            f"Testing network quality to {host}:{port} "
            f"({self.test_count} samples)"
        )

        latencies: List[float] = []

        # Collect samples
        for i in range(self.test_count):
            latency = await self.ping_once(host, port, timeout)
            latencies.append(latency)

            # Small delay between pings (except last one)
            if i < self.test_count - 1:
                await asyncio.sleep(interval)

        # Separate successful and failed pings
        successful = [l for l in latencies if l > 0]
        failed_count = len([l for l in latencies if l < 0])

        # Calculate packet loss
        packet_loss = (failed_count / self.test_count) * 100

        # If all packets lost, return early
        if not successful:
            return NetworkQualityResult(
                packet_loss_percent=100.0,
                jitter_ms=0.0,
                avg_latency_ms=0.0,
                min_latency_ms=0.0,
                max_latency_ms=0.0,
                samples=self.test_count
            )

        # Calculate statistics
        avg_latency = statistics.mean(successful)
        min_latency = min(successful)
        max_latency = max(successful)

        # Calculate jitter (standard deviation of latency)
        jitter = statistics.stdev(successful) if len(successful) > 1 else 0.0

        result = NetworkQualityResult(
            packet_loss_percent=round(packet_loss, 2),
            jitter_ms=round(jitter, 2),
            avg_latency_ms=round(avg_latency, 2),
            min_latency_ms=round(min_latency, 2),
            max_latency_ms=round(max_latency, 2),
            samples=self.test_count
        )

        logger.info(
            f"Quality test complete: "
            f"Loss={result.packet_loss_percent}%, "
            f"Jitter={result.jitter_ms}ms, "
            f"Avg={result.avg_latency_ms}ms, "
            f"Score={result.quality_score:.1f}/100"
        )

        return result


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