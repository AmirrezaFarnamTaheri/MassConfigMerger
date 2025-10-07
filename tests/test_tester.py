from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.config import Settings
from configstream.tester import NodeTester


@pytest.mark.asyncio
@patch("configstream.tester.NodeTester.resolve_host", new_callable=AsyncMock)
@patch("asyncio.open_connection")
async def test_node_tester_test_connection_success(
    mock_open_connection: MagicMock, mock_resolve_host: AsyncMock
):
    """Test a successful connection in NodeTester."""
    settings = Settings()
    settings.processing.enable_url_testing = True
    tester = NodeTester(settings)

    # Make the resolver return a valid IP to isolate the connection logic
    mock_resolve_host.return_value = "1.2.3.4"

    mock_reader = AsyncMock()
    mock_writer = MagicMock(spec=asyncio.StreamWriter)
    mock_writer.wait_closed = AsyncMock()
    mock_open_connection.return_value = (mock_reader, mock_writer)

    latency = await tester.test_connection("example.com", 443)

    assert latency is not None and latency > 0
    mock_resolve_host.assert_awaited_once_with("example.com")
    mock_open_connection.assert_awaited_once_with("1.2.3.4", 443)
    mock_writer.close.assert_called_once()
    mock_writer.wait_closed.assert_awaited_once()


@pytest.mark.asyncio
@patch("configstream.tester.AsyncResolver")
@patch("asyncio.open_connection")
async def test_node_tester_with_dns_resolve(
    mock_open_connection: MagicMock, MockAsyncResolver: MagicMock
):
    """Test connection logic with successful DNS resolution."""
    settings = Settings()
    settings.processing.enable_url_testing = True
    tester = NodeTester(settings)

    mock_resolver = MockAsyncResolver.return_value
    mock_resolver.resolve = AsyncMock(return_value=[{'host': '1.2.3.4'}])

    mock_reader = AsyncMock()
    mock_writer = MagicMock(spec=asyncio.StreamWriter)
    mock_writer.wait_closed = AsyncMock()
    mock_open_connection.return_value = (mock_reader, mock_writer)

    await tester.test_connection("example.com", 443)

    mock_resolver.resolve.assert_awaited_once()
    assert mock_resolver.resolve.await_args.args == ("example.com",)
    mock_open_connection.assert_awaited_once_with("1.2.3.4", 443)
    mock_writer.close.assert_called_once()
    mock_writer.wait_closed.assert_awaited_once()


@pytest.mark.asyncio
async def test_node_tester_disabled():
    """Test that no connection is attempted if url testing is disabled."""
    settings = Settings()
    settings.processing.enable_url_testing = False
    tester = NodeTester(settings)

    with patch("asyncio.open_connection") as mock_open_connection:
        latency = await tester.test_connection("example.com", 443)
        assert latency is None
        mock_open_connection.assert_not_called()


@pytest.mark.asyncio
@patch("configstream.tester.Reader")
@patch("configstream.tester.NodeTester.resolve_host", new_callable=AsyncMock)
async def test_lookup_geo_data_success(
    mock_resolve_host: AsyncMock, MockReader: MagicMock
):
    """Test a successful GeoIP lookup."""
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    tester = NodeTester(settings)

    mock_resolve_host.return_value = "1.2.3.4"
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
    mock_resolve_host.assert_awaited_once_with("example.com")
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

    # Mock the private attributes that the close method targets
    mock_resolver = AsyncMock()
    tester._resolver = mock_resolver

    mock_geoip_reader = MagicMock()
    tester._geoip_reader = mock_geoip_reader

    # Mock the helper method to isolate the close logic
    with patch.object(tester, "_close_resource", new_callable=AsyncMock) as mock_close_resource:
        await tester.close()

        # Assert that the close helper was called for each resource
        mock_close_resource.assert_any_call(mock_resolver, "Resolver")
        mock_close_resource.assert_any_call(mock_geoip_reader, "GeoIP reader")
        assert mock_close_resource.call_count == 2

        # Assert that the attributes are cleared
        assert tester._resolver is None
        assert tester._geoip_reader is None


import socket
import logging
from configstream.tester import is_ip_address

def test_is_ip_address_invalid():
    """Test that is_ip_address returns False for an invalid IP."""
    assert not is_ip_address("not-an-ip")

@patch("configstream.tester.AsyncResolver", side_effect=Exception("Resolver Error"))
def test_get_resolver_init_failure(MockAsyncResolver, caplog):
    """Test that the resolver is not created if initialization fails."""
    caplog.set_level(logging.DEBUG)
    settings = Settings()
    tester = NodeTester(settings)
    assert tester._get_resolver() is None
    assert "AsyncResolver init failed" in caplog.text

@patch("configstream.tester.Reader", side_effect=OSError("GeoIP DB not found"))
def test_get_geoip_reader_init_failure(MockReader, caplog):
    """Test that the GeoIP reader is not created if initialization fails."""
    caplog.set_level(logging.ERROR)
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    tester = NodeTester(settings)
    assert tester._get_geoip_reader() is None
    assert "GeoIP reader init failed" in caplog.text

@pytest.mark.asyncio
@patch("configstream.tester.AsyncResolver")
async def test_resolve_host_all_failures(MockAsyncResolver, caplog):
    """Test resolve_host returns None if all lookups fail."""
    caplog.set_level(logging.DEBUG)
    settings = Settings()
    tester = NodeTester(settings)

    mock_resolver = MockAsyncResolver.return_value
    mock_resolver.resolve.side_effect = Exception("Async DNS Error")

    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.getaddrinfo.side_effect = socket.gaierror(
            "Standard DNS error"
        )
        ip = await tester.resolve_host("example.com")
        assert ip is None
        assert "Async DNS resolve failed" in caplog.text
        assert "Standard DNS lookup failed" in caplog.text

@pytest.mark.asyncio
@patch("configstream.tester.NodeTester.resolve_host", new_callable=AsyncMock, return_value="1.2.3.4")
@patch("asyncio.open_connection", side_effect=OSError("Connection failed"))
async def test_test_connection_failure(mock_open_connection, mock_resolve_host, caplog):
    """Test that test_connection returns None on connection failure."""
    caplog.set_level(logging.DEBUG)
    settings = Settings()
    tester = NodeTester(settings)
    latency = await tester.test_connection("example.com", 443)
    assert latency is None
    assert "Connection test failed for example.com:443" in caplog.text

@pytest.mark.asyncio
@patch("configstream.tester.Reader")
@patch("configstream.tester.NodeTester.resolve_host", new_callable=AsyncMock, return_value="1.2.3.4")
async def test_lookup_geo_data_geoip_error(mock_resolve_host, MockReader, caplog):
    """Test that lookup_geo_data returns None if the GeoIP lookup fails."""
    caplog.set_level(logging.DEBUG)
    from configstream.tester import AddressNotFoundError
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    tester = NodeTester(settings)

    mock_reader_instance = MockReader.return_value
    type(mock_reader_instance).city = MagicMock(side_effect=AddressNotFoundError("IP not found"))

    geo_data = await tester.lookup_geo_data("example.com")
    assert geo_data == (None, None, None, None)
    assert "GeoIP lookup failed" in caplog.text

@pytest.mark.asyncio
async def test_close_resource_failure(caplog):
    """Test that _close_resource handles exceptions during close."""
    caplog.set_level(logging.DEBUG)
    settings = Settings()
    tester = NodeTester(settings)

    mock_resource = MagicMock()
    mock_resource.close.side_effect = Exception("Close error")

    await tester._close_resource(mock_resource, "TestResource")
    assert "TestResource close failed: Close error" in caplog.text

@patch("configstream.tester.Reader", None)
def test_geoip_not_installed():
    """Test that lookup_country returns None if geoip2 is not installed."""
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    tester = NodeTester(settings)
    assert tester._get_geoip_reader() is None

@patch("configstream.tester.AsyncResolver", None)
@pytest.mark.asyncio
async def test_aiodns_not_installed():
    """Test that resolve_host uses standard DNS if aiodns is not installed."""
    settings = Settings()
    tester = NodeTester(settings)

    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.getaddrinfo = AsyncMock(return_value=[
            (None, None, None, None, ("1.2.3.4", 0))
        ])
        ip = await tester.resolve_host("example.com")
        assert ip == "1.2.3.4"
        mock_loop.return_value.getaddrinfo.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_host_caching():
    """Test that DNS results are cached."""
    settings = Settings()
    tester = NodeTester(settings)

    with patch.object(tester, '_get_resolver') as mock_get_resolver:
        mock_resolver = AsyncMock()
        mock_resolver.resolve.return_value = [{'host': '1.2.3.4'}]
        mock_get_resolver.return_value = mock_resolver

        # First call, should use resolver
        ip1 = await tester.resolve_host("example.com")
        assert ip1 == "1.2.3.4"
        mock_resolver.resolve.assert_awaited_once_with("example.com")
        assert "example.com" in tester.dns_cache
        assert tester.dns_cache["example.com"] == "1.2.3.4"

        # Second call, should use cache
        ip2 = await tester.resolve_host("example.com")
        assert ip2 == "1.2.3.4"
        # Assert that resolve was not called again
        mock_resolver.resolve.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_host_with_ip_address():
    """Test that resolve_host returns the IP directly if an IP is passed."""
    settings = Settings()
    tester = NodeTester(settings)
    with patch.object(tester, '_get_resolver') as mock_get_resolver:
        ip = await tester.resolve_host("1.1.1.1")
        assert ip == "1.1.1.1"
        mock_get_resolver.assert_not_called()


@pytest.mark.asyncio
@patch("configstream.tester.NodeTester.resolve_host", new_callable=AsyncMock, return_value=None)
async def test_test_connection_unresolved_host(mock_resolve_host, caplog):
    """Test that test_connection skips if host cannot be resolved."""
    caplog.set_level(logging.DEBUG)
    settings = Settings()
    tester = NodeTester(settings)
    latency = await tester.test_connection("unresolved.com", 443)
    assert latency is None
    assert "Skipping connection test; unresolved host: unresolved.com" in caplog.text


@pytest.mark.asyncio
@patch("configstream.tester.NodeTester.resolve_host", new_callable=AsyncMock, return_value="10.0.0.2")
async def test_test_connection_private_ip(mock_resolve_host, caplog):
    """Ensure private IPs resolved from hostnames are rejected."""
    caplog.set_level(logging.DEBUG)
    settings = Settings()
    tester = NodeTester(settings)
    with patch("asyncio.open_connection") as mock_open_connection:
        latency = await tester.test_connection("internal.example", 443)
    assert latency is None
    mock_open_connection.assert_not_called()
    assert "non-public IP resolved for internal.example" in caplog.text
    mock_resolve_host.assert_awaited_once()


@pytest.mark.asyncio
@patch("configstream.tester.NodeTester.resolve_host", new_callable=AsyncMock, return_value=None)
async def test_lookup_geo_data_unresolved_host(mock_resolve_host, caplog):
    """Test that lookup_geo_data skips if host cannot be resolved."""
    caplog.set_level(logging.DEBUG)
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    with patch("configstream.tester.Reader"):
        tester = NodeTester(settings)
        geo_data = await tester.lookup_geo_data("unresolved.com")
        assert geo_data == (None, None, None, None)
        assert "Skipping GeoIP lookup; unresolved host: unresolved.com" in caplog.text