from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from massconfigmerger.config import Settings
from massconfigmerger.tester import NodeTester


@pytest.mark.asyncio
@patch("massconfigmerger.tester.NodeTester._resolve_host", new_callable=AsyncMock)
@patch("asyncio.open_connection")
async def test_node_tester_test_connection_success(
    mock_open_connection: MagicMock, mock_resolve_host: AsyncMock
):
    """Test a successful connection in NodeTester."""
    settings = Settings()
    settings.processing.enable_url_testing = True
    tester = NodeTester(settings)

    # Make the resolver return the original host to isolate the connection logic
    mock_resolve_host.return_value = "example.com"

    mock_reader = AsyncMock()
    mock_writer = MagicMock(spec=asyncio.StreamWriter)
    mock_writer.wait_closed = AsyncMock()
    mock_open_connection.return_value = (mock_reader, mock_writer)

    latency = await tester.test_connection("example.com", 443)

    assert latency is not None and latency > 0
    mock_resolve_host.assert_awaited_once_with("example.com")
    mock_open_connection.assert_awaited_once_with("example.com", 443)
    mock_writer.close.assert_called_once()
    mock_writer.wait_closed.assert_awaited_once()


@pytest.mark.asyncio
@patch("massconfigmerger.tester.AsyncResolver")
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

    mock_reader, mock_writer = AsyncMock(), AsyncMock()
    mock_writer.wait_closed = AsyncMock()
    mock_open_connection.return_value = (mock_reader, mock_writer)

    await tester.test_connection("example.com", 443)

    mock_resolver.resolve.assert_awaited_once()
    assert mock_resolver.resolve.await_args.args == ("example.com",)
    mock_open_connection.assert_awaited_once_with("1.2.3.4", 443)


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
@patch("massconfigmerger.tester.Reader")
@patch("massconfigmerger.tester.NodeTester._resolve_host", new_callable=AsyncMock)
async def test_lookup_country_success(
    mock_resolve_host: AsyncMock, MockReader: MagicMock
):
    """Test a successful GeoIP country lookup."""
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    tester = NodeTester(settings)

    mock_resolve_host.return_value = "1.2.3.4"
    mock_reader_instance = MockReader.return_value
    mock_reader_instance.country.return_value.country.iso_code = "US"

    country = await tester.lookup_country("example.com")

    assert country == "US"
    mock_resolve_host.assert_awaited_once_with("example.com")
    MockReader.assert_called_once_with("dummy.mmdb")
    mock_reader_instance.country.assert_called_once_with("1.2.3.4")


@pytest.mark.asyncio
async def test_lookup_country_no_db():
    """Test that lookup is skipped if no GeoIP DB is configured."""
    settings = Settings()
    settings.processing.geoip_db = None
    tester = NodeTester(settings)
    country = await tester.lookup_country("example.com")
    assert country is None


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
from massconfigmerger.tester import _is_ip_address

def test_is_ip_address_invalid():
    """Test that _is_ip_address returns False for an invalid IP."""
    assert not _is_ip_address("not-an-ip")

@patch("massconfigmerger.tester.AsyncResolver", side_effect=Exception("Resolver Error"))
def test_get_resolver_init_failure(MockAsyncResolver, caplog):
    """Test that the resolver is not created if initialization fails."""
    caplog.set_level(logging.DEBUG)
    settings = Settings()
    tester = NodeTester(settings)
    assert tester._get_resolver() is None
    assert "AsyncResolver init failed" in caplog.text

@patch("massconfigmerger.tester.Reader", side_effect=OSError("GeoIP DB not found"))
def test_get_geoip_reader_init_failure(MockReader, caplog):
    """Test that the GeoIP reader is not created if initialization fails."""
    caplog.set_level(logging.ERROR)
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    tester = NodeTester(settings)
    assert tester._get_geoip_reader() is None
    assert "GeoIP reader init failed" in caplog.text

@pytest.mark.asyncio
@patch("massconfigmerger.tester.AsyncResolver")
async def test_resolve_host_all_failures(MockAsyncResolver, caplog):
    """Test _resolve_host returns the original host if all lookups fail."""
    caplog.set_level(logging.DEBUG)
    settings = Settings()
    tester = NodeTester(settings)

    mock_resolver = MockAsyncResolver.return_value
    mock_resolver.resolve.side_effect = Exception("Async DNS Error")

    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.getaddrinfo.side_effect = socket.gaierror("Standard DNS error")
        ip = await tester._resolve_host("example.com")
        assert ip == "example.com"
        assert "Async DNS resolve failed" in caplog.text
        assert "Standard DNS lookup failed" in caplog.text

@pytest.mark.asyncio
@patch("massconfigmerger.tester.NodeTester._resolve_host", new_callable=AsyncMock, return_value="1.2.3.4")
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
@patch("massconfigmerger.tester.Reader")
@patch("massconfigmerger.tester.NodeTester._resolve_host", new_callable=AsyncMock, return_value="1.2.3.4")
async def test_lookup_country_geoip_error(mock_resolve_host, MockReader, caplog):
    """Test that lookup_country returns None if the GeoIP lookup fails."""
    caplog.set_level(logging.DEBUG)
    from massconfigmerger.tester import AddressNotFoundError
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    tester = NodeTester(settings)

    mock_reader_instance = MockReader.return_value
    mock_reader_instance.country.side_effect = AddressNotFoundError("IP not found")

    country = await tester.lookup_country("example.com")
    assert country is None
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

@patch("massconfigmerger.tester.Reader", None)
def test_geoip_not_installed():
    """Test that lookup_country returns None if geoip2 is not installed."""
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    tester = NodeTester(settings)
    assert tester._get_geoip_reader() is None

@patch("massconfigmerger.tester.AsyncResolver", None)
@pytest.mark.asyncio
async def test_aiodns_not_installed():
    """Test that _resolve_host uses standard DNS if aiodns is not installed."""
    settings = Settings()
    tester = NodeTester(settings)

    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.getaddrinfo = AsyncMock(return_value=[
            (None, None, None, None, ("1.2.3.4", 0))
        ])
        ip = await tester._resolve_host("example.com")
        assert ip == "1.2.3.4"
        mock_loop.return_value.getaddrinfo.assert_awaited_once()