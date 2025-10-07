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