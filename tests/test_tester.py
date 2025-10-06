from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from geoip2.errors import AddressNotFoundError

from massconfigmerger.config import Settings
from massconfigmerger.testing import NodeTester
from massconfigmerger.testing.connection import ConnectionTester
from massconfigmerger.testing.dns import DNSResolver, is_ip_address
from massconfigmerger.testing.geoip import GeoIPLookup


@pytest.mark.asyncio
async def test_node_tester_test_connection_success():
    """Test a successful connection in NodeTester."""
    settings = Settings()
    settings.processing.enable_url_testing = True
    tester = NodeTester(settings)

    # Patch the instance methods directly
    tester.resolver.resolve = AsyncMock(return_value="1.2.3.4")
    tester.connection_tester.test = AsyncMock(return_value=0.123)

    latency = await tester.test_connection("example.com", 443)

    assert latency == 0.123
    tester.resolver.resolve.assert_awaited_once_with("example.com")
    tester.connection_tester.test.assert_awaited_once_with("1.2.3.4", 443)


@pytest.mark.asyncio
async def test_node_tester_disabled():
    """Test that no connection is attempted if url testing is disabled."""
    settings = Settings()
    settings.processing.enable_url_testing = False
    tester = NodeTester(settings)

    # Patch the instance method
    tester.connection_tester.test = AsyncMock()

    latency = await tester.test_connection("example.com", 443)

    assert latency is None
    tester.connection_tester.test.assert_not_awaited()


@pytest.mark.asyncio
@patch("massconfigmerger.testing.geoip.Reader")
async def test_lookup_geo_data_success(MockReader: MagicMock):
    """Test a successful GeoIP lookup."""
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    tester = NodeTester(settings)

    # Patch instance methods
    tester.resolver.resolve = AsyncMock(return_value="1.2.3.4")

    mock_reader_instance = MockReader.return_value
    mock_city_response = MagicMock()
    mock_city_response.country.iso_code = "US"
    mock_city_response.traits.isp = "Google"
    mock_city_response.location.latitude = 37.7749
    mock_city_response.location.longitude = -122.4194
    type(mock_reader_instance).city = MagicMock(return_value=mock_city_response)

    country, isp, lat, lon = await tester.lookup_geo_data("example.com")

    assert country == "US"
    assert isp == "Google"
    assert lat == 37.7749
    assert lon == -122.4194
    tester.resolver.resolve.assert_awaited_once_with("example.com")
    MockReader.assert_called_once_with("dummy.mmdb")
    mock_reader_instance.city.assert_called_once_with("1.2.3.4")


@pytest.mark.asyncio
async def test_lookup_geo_data_no_db():
    """Test that lookup is skipped if no GeoIP DB is configured."""
    settings = Settings()
    settings.processing.geoip_db = None
    tester = NodeTester(settings)
    geo_data = await tester.lookup_geo_data("example.com")
    assert geo_data == (None, None, None, None)


@pytest.mark.asyncio
async def test_close():
    """Test the close method."""
    settings = Settings()
    tester = NodeTester(settings)

    # Mock the components on the instance
    tester.resolver = AsyncMock()
    tester.geoip_lookup = MagicMock()  # GeoIPLookup.close is synchronous

    await tester.close()

    tester.resolver.close.assert_awaited_once()
    tester.geoip_lookup.close.assert_called_once()  # Use assert_called_once for sync method


def test_is_ip_address_invalid():
    """Test that is_ip_address returns False for an invalid IP."""
    assert not is_ip_address("not-an-ip")


@patch("massconfigmerger.testing.dns.AsyncResolver", side_effect=Exception("Resolver Error"))
def test_get_resolver_init_failure(MockAsyncResolver, caplog):
    """Test that the resolver is not created if initialization fails."""
    caplog.set_level(logging.DEBUG)
    resolver = DNSResolver()
    assert resolver._get_async_resolver() is None
    assert "AsyncResolver init failed" in caplog.text


@patch("massconfigmerger.testing.geoip.Reader", side_effect=OSError("GeoIP DB not found"))
def test_get_geoip_reader_init_failure(MockReader, caplog):
    """Test that the GeoIP reader is not created if initialization fails."""
    caplog.set_level(logging.ERROR)
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    resolver = DNSResolver()
    geoip = GeoIPLookup(settings, resolver)
    assert geoip._get_reader() is None
    assert "GeoIP reader init failed" in caplog.text


@pytest.mark.asyncio
@patch("massconfigmerger.testing.dns.AsyncResolver")
async def test_resolve_host_all_failures(MockAsyncResolver, caplog):
    """Test resolve_host returns None if all lookups fail."""
    import socket

    caplog.set_level(logging.DEBUG)
    resolver = DNSResolver()
    mock_async_resolver = MockAsyncResolver.return_value
    mock_async_resolver.resolve.side_effect = Exception("Async DNS Error")
    resolver._resolver = mock_async_resolver

    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.getaddrinfo.side_effect = socket.gaierror(
            "Standard DNS error"
        )
        ip = await resolver.resolve("example.com")
        assert ip is None
        assert "Async DNS resolve failed" in caplog.text
        assert "Standard DNS lookup failed" in caplog.text


@pytest.mark.asyncio
@patch(
    "massconfigmerger.testing.connection.asyncio.open_connection",
    side_effect=OSError("Connection failed"),
)
async def test_test_connection_failure(mock_open_connection, caplog):
    """Test that test_connection returns None on connection failure."""
    caplog.set_level(logging.DEBUG)
    tester = ConnectionTester(connect_timeout=1.0)
    latency = await tester.test("1.2.3.4", 443)
    assert latency is None
    assert "Connection test failed for 1.2.3.4:443" in caplog.text


@pytest.mark.asyncio
@patch("massconfigmerger.testing.geoip.Reader")
async def test_lookup_geo_data_geoip_error(MockReader, caplog):
    """Test that lookup_geo_data returns None if the GeoIP lookup fails."""
    caplog.set_level(logging.DEBUG)
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    resolver = DNSResolver()
    # Patch the instance method
    resolver.resolve = AsyncMock(return_value="1.2.3.4")

    tester = GeoIPLookup(settings, resolver)

    mock_reader_instance = MockReader.return_value
    type(mock_reader_instance).city = MagicMock(
        side_effect=AddressNotFoundError("IP not found")
    )
    tester._geoip_reader = mock_reader_instance

    geo_data = await tester.lookup("example.com")
    assert geo_data == (None, None, None, None)
    assert "GeoIP lookup failed" in caplog.text