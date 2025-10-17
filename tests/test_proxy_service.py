import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from configstream.core import Proxy
from configstream.events import Event, EventBus, EventType
from configstream.proxy_service import ProxyService
from configstream.services import IProxyRepository, IProxyTester


class TestProxyService(unittest.TestCase):

    def setUp(self):
        self.repository = MagicMock(spec=IProxyRepository)
        self.tester = MagicMock(spec=IProxyTester)
        self.event_bus = MagicMock(spec=EventBus)
        self.service = ProxyService(
            repository=self.repository, tester=self.tester, event_bus=self.event_bus
        )

        # Async mocks
        self.repository.save = AsyncMock()
        self.tester.test = AsyncMock()
        self.event_bus.publish = AsyncMock()

    def test_process_working_proxy(self):
        asyncio.run(self.process_working_proxy_async())

    async def process_working_proxy_async(self):
        proxy = Proxy(config="test://proxy", protocol="test", address="proxy", port=8080)
        tested_proxy = Proxy(
            config="test://proxy",
            protocol="test",
            address="proxy",
            port=8080,
            is_working=True,
            latency=100,
        )
        self.tester.test.return_value = tested_proxy

        await self.service.process_proxy(proxy)

        self.tester.test.assert_called_once_with(proxy)
        self.event_bus.publish.assert_called_once()
        self.repository.save.assert_called_once_with(tested_proxy)

        # Check the event data
        published_event: Event = self.event_bus.publish.call_args[0][0]
        self.assertEqual(published_event.type, EventType.PROXY_TESTED)
        self.assertEqual(published_event.data["proxy"], tested_proxy)

    def test_process_failed_proxy(self):
        asyncio.run(self.process_failed_proxy_async())

    async def process_failed_proxy_async(self):
        proxy = Proxy(config="test://proxy", protocol="test", address="proxy", port=8080)
        tested_proxy = Proxy(
            config="test://proxy", protocol="test", address="proxy", port=8080, is_working=False
        )
        self.tester.test.return_value = tested_proxy

        await self.service.process_proxy(proxy)

        self.tester.test.assert_called_once_with(proxy)
        self.event_bus.publish.assert_called_once()
        self.repository.save.assert_called_once_with(tested_proxy)

        # Check the event data
        published_event: Event = self.event_bus.publish.call_args[0][0]
        self.assertEqual(published_event.type, EventType.PROXY_FAILED)
        self.assertEqual(published_event.data["proxy"], tested_proxy)
        self.assertIn("error", published_event.data)


if __name__ == "__main__":
    unittest.main()
