import asyncio
import types
import pytest

from massconfigmerger.tester import NodeTester
from massconfigmerger.config import Settings
from massconfigmerger import vpn_retester


class DummyResolver:
    def __init__(self):
        self.closed = False

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_node_tester_close():
    tester = NodeTester(Settings())
    dummy = DummyResolver()
    tester.resolver = dummy
    await tester.close()
    assert dummy.closed
    assert tester.resolver is None


@pytest.mark.asyncio
async def test_retest_configs_closes_tester(monkeypatch):
    closed = False

    class DummyTester:
        async def test_connection(self, host, port):
            return 0.1

        async def close(self) -> None:
            nonlocal closed
            closed = True

    class DummyProcessor:
        def __init__(self):
            self.tester = DummyTester()

        def extract_host_port(self, cfg):
            return "example.com", 80

        async def test_connection(self, host, port):
            return await self.tester.test_connection(host, port)

    monkeypatch.setattr(vpn_retester, "EnhancedConfigProcessor", DummyProcessor)

    await vpn_retester.retest_configs(["dummy"])
    assert closed
