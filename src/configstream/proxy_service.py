from __future__ import annotations

from datetime import datetime, timezone

from .core import Proxy
from .events import Event, EventBus, EventType
from .services import IProxyRepository, IProxyTester


class ProxyService:
    """Service with injected dependencies"""

    def __init__(
        self,
        repository: IProxyRepository,
        tester: IProxyTester,
        event_bus: EventBus,
    ):
        self.repository = repository
        self.tester = tester
        self.event_bus = event_bus

    async def process_proxy(self, proxy: Proxy) -> None:
        """Process a single proxy"""
        # Test
        tested_proxy = await self.tester.test(proxy)

        # Emit event
        if tested_proxy.success:
            await self.event_bus.publish(
                Event(
                    type=EventType.PROXY_TESTED,
                    timestamp=datetime.now(timezone.utc),
                    data={"proxy": tested_proxy.proxy},
                ))
        else:
            await self.event_bus.publish(
                Event(
                    type=EventType.PROXY_FAILED,
                    timestamp=datetime.now(timezone.utc),
                    data={
                        "proxy": tested_proxy.proxy,
                        "error": "Failed connectivity test"
                    },
                ))

        # Save
        await self.repository.save(tested_proxy.proxy)
