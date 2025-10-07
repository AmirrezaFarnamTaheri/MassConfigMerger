from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

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


def test_is_public_ip_helper():
    """Ensure the helper correctly identifies public versus private IPs."""

    settings = Settings()
    tester = NodeTester(settings)
    assert tester._is_public_ip("8.8.8.8") is True
    assert tester._is_public_ip("10.0.0.1") is False
    assert tester._is_public_ip("invalid") is False


@pytest.mark.asyncio
async def test_lookup_geo_data_uses_ip_cache(monkeypatch):
    """Lookups reuse cached geo data keyed by resolved IP addresses."""

    settings = Settings()
    tester = NodeTester(settings)
    cached = ("US", "ISP", 10.0, 20.0)
    tester.geoip_cache["8.8.4.4"] = cached

    monkeypatch.setattr(tester, "resolve_host", AsyncMock(return_value="8.8.4.4"))
    tester._get_geoip_reader = MagicMock(return_value=MagicMock())  # type: ignore[method-assign]

    result = await tester.lookup_geo_data("example.com")

    assert result == cached
    tester._get_geoip_reader.assert_called_once()
    tester.resolve_host.assert_awaited_once_with("example.com")  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_lookup_geo_data_skips_private_ip(monkeypatch):
    """Private IP addresses should not trigger GeoIP lookups."""

    settings = Settings()
    tester = NodeTester(settings)

    monkeypatch.setattr(tester, "resolve_host", AsyncMock(return_value="10.0.0.5"))
    reader = MagicMock()
    tester._get_geoip_reader = MagicMock(return_value=reader)  # type: ignore[method-assign]

    result = await tester.lookup_geo_data("internal.example")

    assert result == (None, None, None, None)
    reader.city.assert_not_called()
    reader.country.assert_not_called()


@pytest.mark.asyncio
async def test_lookup_geo_data_caches_host_and_ip(monkeypatch):
    """Resolved geo data is cached for both hostnames and IP addresses."""

    settings = Settings()
    tester = NodeTester(settings)
    ip_address = "8.8.8.8"

    city_response = SimpleNamespace(
        country=SimpleNamespace(iso_code="DE"),
        traits=SimpleNamespace(isp="Example ISP"),
        location=SimpleNamespace(latitude=52.5, longitude=13.4),
    )
    reader = MagicMock()
    reader.city.return_value = city_response
    tester._get_geoip_reader = MagicMock(return_value=reader)  # type: ignore[method-assign]
    monkeypatch.setattr(tester, "resolve_host", AsyncMock(return_value=ip_address))

    result = await tester.lookup_geo_data("geo.example")

    assert result == ("DE", "Example ISP", 52.5, 13.4)
    assert tester.geoip_cache["geo.example"] == result
    assert tester.geoip_cache[ip_address] == result