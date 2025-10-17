from __future__ import annotations

from datetime import datetime, timezone

from .core import Proxy
from .events import Event, EventBus, EventType
from .services import IProxyRepository, IProxyTester
from .security.advanced_tests import AdvancedSecurityTester
from .benchmarks import ProxyBenchmark


class ProxyService:
    """Service with injected dependencies"""

    def __init__(
        self,
        repository: IProxyRepository,
        tester: IProxyTester,
        event_bus: EventBus,
        security_tester: AdvancedSecurityTester,
        benchmark: ProxyBenchmark,
    ):
        self.repository = repository
        self.tester = tester
        self.event_bus = event_bus
        self.security_tester = security_tester
        self.benchmark = benchmark

    async def process_proxy(self, proxy: Proxy) -> None:
        """Process a single proxy"""
        # Test
        tested_proxy = await self.tester.test(proxy)

        # Emit event
        if tested_proxy.is_working:
            await self.event_bus.publish(
                Event(
                    type=EventType.PROXY_TESTED,
                    timestamp=datetime.now(timezone.utc),
                    data={"proxy": tested_proxy},
                )
            )

            # Run advanced tests
            security_results = await self.security_tester.run_all_tests(tested_proxy, self.tester)
            tested_proxy.security_issues.extend([f"{test}: {res['description']}" for test, res in security_results.items() if not res.get('passed')])

            # Run benchmarks
            latency_benchmark = await self.benchmark.benchmark_latency(tested_proxy, self.tester)
            if latency_benchmark:
                tested_proxy.latency = latency_benchmark.avg_time

            throughput_benchmark = await self.benchmark.benchmark_throughput(tested_proxy, self.tester)
            if throughput_benchmark:
                # Add throughput to proxy details
                pass

            stability_benchmark = await self.benchmark.benchmark_stability(tested_proxy, self.tester)
            if stability_benchmark:
                # Add stability to proxy details
                pass

        else:
            await self.event_bus.publish(
                Event(
                    type=EventType.PROXY_FAILED,
                    timestamp=datetime.now(timezone.utc),
                    data={"proxy": tested_proxy, "error": "Failed connectivity test"},
                )
            )

        # Save
        await self.repository.save(tested_proxy)
