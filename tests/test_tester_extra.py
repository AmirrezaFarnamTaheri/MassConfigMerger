from __future__ import annotations

import sys
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from configstream.config import Settings
from configstream.tester import NodeTester, is_ip_address


@pytest.mark.asyncio
async def test_lookup_geo_data_empty_host():
    """Test lookup_geo_data with an empty host string."""
    settings = Settings()
    tester = NodeTester(settings)
    result = await tester.lookup_geo_data("")
    assert result == (None, None, None, None)


@patch("configstream.tester.Reader", side_effect=ValueError("Test ValueError"))
def test_get_geoip_reader_value_error(mock_reader, caplog):
    """Test _get_geoip_reader handles ValueError on init."""
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    tester = NodeTester(settings)

    reader = tester._get_geoip_reader()

    assert reader is None
    assert "GeoIP reader init failed" in caplog.text


@pytest.mark.asyncio
async def test_close_resource_callable_not_coro():
    """Test _close_resource with a synchronous, callable close method."""
    settings = Settings()
    tester = NodeTester(settings)

    mock_resource = MagicMock()
    mock_resource.close = MagicMock() # A regular MagicMock is callable but not a coroutine

    await tester._close_resource(mock_resource, "TestResource")

    mock_resource.close.assert_called_once()


def test_missing_geoip2_dependency():
    """Test that NodeTester handles a missing geoip2 dependency."""
    with patch.dict(sys.modules, {"geoip2": None}):
        settings = Settings()
        settings.processing.geoip_db = "dummy.mmdb"
        tester = NodeTester(settings)
        # _get_geoip_reader should return None without raising an error
        assert tester._get_geoip_reader() is None


def test_missing_aiodns_dependency():
    """Test that NodeTester handles a missing aiodns dependency."""
    with patch.dict(sys.modules, {"aiohttp.resolver": None, "aiodns": None}):
        settings = Settings()
        tester = NodeTester(settings)
        # _get_resolver should return None without raising an error
        assert tester._get_resolver() is None


@pytest.mark.asyncio
async def test_resolve_host_rejects_private_ip():
    """Ensure plain private IP inputs are not cached or returned."""
    settings = Settings()
    tester = NodeTester(settings)
    ip = await tester.resolve_host("192.168.1.10")
    assert ip is None
    assert "192.168.1.10" not in tester.dns_cache


@pytest.mark.asyncio
async def test_resolve_host_filters_private_from_resolver(monkeypatch):
    """Reject private addresses returned by async resolvers."""
    settings = Settings()
    tester = NodeTester(settings)

    mock_resolver = AsyncMock()
    mock_resolver.resolve.return_value = [{"host": "10.0.0.5"}]
    monkeypatch.setattr(tester, "_get_resolver", lambda: mock_resolver)

    ip = await tester.resolve_host("internal.example")
    assert ip is None
    mock_resolver.resolve.assert_awaited_once_with("internal.example")
    assert "internal.example" not in tester.dns_cache