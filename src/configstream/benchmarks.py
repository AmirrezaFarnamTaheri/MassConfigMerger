import asyncio
import time
from typing import List, Dict
from dataclasses import dataclass
import statistics

from .core import Proxy
from .testers import SingBoxTester

@dataclass
class BenchmarkResult:
    """Benchmark result"""
    test_name: str
    min_time: float
    max_time: float
    avg_time: float
    median_time: float
    std_dev: float
    samples: int

class ProxyBenchmark:
    """Comprehensive proxy benchmarking"""

    async def benchmark_latency(
        self,
        proxy: Proxy,
        worker: SingBoxTester,
        samples: int = 10
    ) -> BenchmarkResult:
        """Benchmark latency with multiple samples"""
        times = []

        for _ in range(samples):
            start = time.perf_counter()
            try:
                # This is a placeholder. In a real scenario, you would
                # use the worker to test connectivity.
                await asyncio.sleep(0.1)
                elapsed = time.perf_counter() - start
                times.append(elapsed * 1000)  # Convert to ms
            except:
                pass

            await asyncio.sleep(0.1)  # Small delay between tests

        if not times:
            return None

        return BenchmarkResult(
            test_name="latency",
            min_time=min(times),
            max_time=max(times),
            avg_time=statistics.mean(times),
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            samples=len(times)
        )

    async def benchmark_throughput(
        self,
        proxy: Proxy,
        worker: SingBoxTester
    ) -> Dict[str, float]:
        """Benchmark download/upload speeds"""
        # Download test
        download_url = "https://httpbin.org/bytes/1048576"  # 1MB

        start = time.perf_counter()
        try:
            # This is a placeholder. In a real scenario, you would
            # use the worker to fetch the URL.
            await asyncio.sleep(0.5)
            download_time = time.perf_counter() - start
            download_speed = 1.0 / download_time  # MB/s
        except:
            download_speed = 0

        # Upload test
        upload_url = "https://httpbin.org/post"
        upload_data = b"x" * 1048576  # 1MB

        start = time.perf_counter()
        try:
            # This is a placeholder. In a real scenario, you would
            # use the worker to post the data.
            await asyncio.sleep(0.5)
            upload_time = time.perf_counter() - start
            upload_speed = 1.0 / upload_time  # MB/s
        except:
            upload_speed = 0

        return {
            'download_speed_mbps': download_speed,
            'upload_speed_mbps': upload_speed
        }

    async def benchmark_stability(
        self,
        proxy: Proxy,
        worker: SingBoxTester,
        duration: int = 60
    ) -> Dict[str, any]:
        """Test connection stability over time"""
        start_time = time.time()
        successful_requests = 0
        failed_requests = 0

        while time.time() - start_time < duration:
            try:
                # This is a placeholder. In a real scenario, you would
                # use the worker to test connectivity.
                await asyncio.sleep(0.1)
                successful_requests += 1
            except:
                failed_requests += 1

            await asyncio.sleep(5)  # Test every 5 seconds

        total = successful_requests + failed_requests
        stability_score = successful_requests / total if total > 0 else 0

        return {
            'duration': duration,
            'successful': successful_requests,
            'failed': failed_requests,
            'stability_score': stability_score
        }