import asyncio
import types
import sys
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


@pytest.mark.asyncio
async def test_node_tester_close_geoip_reader(monkeypatch):
    tester = NodeTester(Settings())
    monkeypatch.setattr(tester.config, "geoip_db", "dummy.mmdb")

    class DummyCountry:
        iso_code = "US"

    class DummyReader:
        def __init__(self, path):
            self.closed = False

        def country(self, ip):
            return types.SimpleNamespace(country=DummyCountry())

        def close(self):
            self.closed = True

    dummy_geoip2 = types.ModuleType("geoip2")
    dummy_database = types.ModuleType("geoip2.database")
    dummy_errors = types.ModuleType("geoip2.errors")
    class DummyAddressNotFoundError(Exception):
        pass
    dummy_errors.AddressNotFoundError = DummyAddressNotFoundError
    dummy_database.Reader = DummyReader
    dummy_geoip2.database = dummy_database
    dummy_geoip2.errors = dummy_errors
    monkeypatch.setitem(sys.modules, "geoip2", dummy_geoip2)
    monkeypatch.setitem(sys.modules, "geoip2.database", dummy_database)
    monkeypatch.setitem(sys.modules, "geoip2.errors", dummy_errors)

    await tester.lookup_country("1.2.3.4")
    reader = tester._geoip_reader

    await tester.close()
    assert isinstance(reader, DummyReader) and reader.closed
    assert tester._geoip_reader is None
