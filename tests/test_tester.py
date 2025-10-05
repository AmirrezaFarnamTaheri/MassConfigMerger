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

    mock_resolver = AsyncMock()
    mock_resolver.close = AsyncMock()
    tester.resolver = mock_resolver

    mock_geoip_reader = MagicMock()
    mock_geoip_reader.close = MagicMock()
    tester._geoip_reader = mock_geoip_reader

    await tester.close()

    mock_resolver.close.assert_awaited_once()
    mock_geoip_reader.close.assert_called_once()
    assert tester.resolver is None
    assert tester._geoip_reader is None