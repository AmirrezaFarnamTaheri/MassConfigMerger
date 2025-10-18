import asyncio

import pytest
from aiohttp import web

from configstream.fetcher import FetchResult, fetch_multiple_sources


@pytest.mark.asyncio
async def test_fetch_multiple_sources_success(aiohttp_client):
    """Test successful fetching from multiple sources."""

    async def handler_one(request):
        return web.Response(text="vmess://proxy1")

    async def handler_two(request):
        return web.Response(text="vless://proxy2")

    app = web.Application()
    app.router.add_get("/one", handler_one)
    app.router.add_get("/two", handler_two)
    client = await aiohttp_client(app)

    source_one = str(client.server.make_url("/one"))
    source_two = str(client.server.make_url("/two"))

    results = await fetch_multiple_sources([source_one, source_two])

    assert len(results) == 2
    assert results[source_one].success is True
    assert results[source_one].configs == ["vmess://proxy1"]
    assert results[source_two].success is True
    assert results[source_two].configs == ["vless://proxy2"]


@pytest.mark.asyncio
async def test_fetch_multiple_sources_with_failures(aiohttp_client):
    """Test fetching from multiple sources with some failures."""

    async def handler_success(request):
        return web.Response(text="vmess://proxy1")

    async def handler_failure(request):
        return web.Response(status=500)

    app = web.Application()
    app.router.add_get("/success", handler_success)
    app.router.add_get("/failure", handler_failure)
    client = await aiohttp_client(app)

    source_success = str(client.server.make_url("/success"))
    source_failure = str(client.server.make_url("/failure"))

    results = await fetch_multiple_sources([source_success, source_failure])

    assert len(results) == 2
    assert results[source_success].success is True
    assert results[source_success].configs == ["vmess://proxy1"]
    assert results[source_failure].success is False
    assert "Server error: 500" in results[source_failure].error


@pytest.mark.asyncio
async def test_fetch_multiple_sources_with_timeout(aiohttp_client):
    """Test fetching from multiple sources with a timeout."""

    async def handler_success(request):
        return web.Response(text="vmess://proxy1")

    async def handler_timeout(request):
        await asyncio.sleep(2)
        return web.Response(text="vless://proxy2")

    app = web.Application()
    app.router.add_get("/success", handler_success)
    app.router.add_get("/timeout", handler_timeout)
    client = await aiohttp_client(app)

    source_success = str(client.server.make_url("/success"))
    source_timeout = str(client.server.make_url("/timeout"))

    results = await fetch_multiple_sources([source_success, source_timeout],
                                           timeout=1)

    assert len(results) == 2
    assert results[source_success].success is True
    assert results[source_success].configs == ["vmess://proxy1"]
    assert results[source_timeout].success is False
    assert "Timeout" in results[source_timeout].error


@pytest.mark.asyncio
async def test_fetch_from_invalid_url():
    """Test that an invalid URL is handled correctly."""
    results = await fetch_multiple_sources(["invalid-url"])
    assert len(results) == 1
    assert results["invalid-url"].success is False
    assert "Invalid URL format" in results["invalid-url"].error


@pytest.mark.asyncio
async def test_fetch_from_source_invalid_url():
    """Test that an invalid URL is handled correctly."""
    session = MagicMock()
    result = await fetch_from_source(session, "this-is-not-a-url")
    assert not result.success
    assert "Invalid URL format" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_rate_limit_error():
    """Test that a 429 status code with a Retry-After header is handled."""
    mock_session = MagicMock()
    mock_context_manager = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 429
    mock_response.headers = {"Retry-After": "60"}
    mock_context_manager.__aenter__.return_value = mock_response
    mock_session.get.return_value = mock_context_manager

    result = await fetch_from_source(mock_session,
                                     "http://example.com",
                                     max_retries=1)
    assert not result.success
    assert "Rate limited" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_server_error():
    """Test that a 5xx server error is handled and retried."""
    mock_session = MagicMock()

    # Mock the response to return a 503 error on the first two attempts
    mock_response_503 = AsyncMock()
    mock_response_503.status = 503
    mock_response_503.request_info = MagicMock()
    mock_response_503.history = []
    mock_response_503.headers = {"Content-Type": "text/plain"}
    # This is needed because raise_for_status is called on it
    mock_response_503.raise_for_status.side_effect = Exception("Server Error")


    # The third attempt will be successful
    mock_response_200 = AsyncMock()
    mock_response_200.status = 200
    mock_response_200.text = AsyncMock(return_value="vless://proxy")
    mock_response_200.headers = {"Content-Type": "text/plain"}


    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.side_effect = [
        mock_response_503, mock_response_503, mock_response_200
    ]
    mock_session.get.return_value = mock_context_manager

    result = await fetch_from_source(mock_session,
                                     "http://example.com",
                                     max_retries=3,
                                     retry_delay=0.1)
    assert result.success
    assert len(result.configs) == 1
    assert mock_session.get.call_count == 3


@pytest.mark.asyncio
async def test_fetch_from_source_unexpected_content_type(caplog):
    """Test that a warning is logged for unexpected content types."""
    mock_session = MagicMock()
    mock_context_manager = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.text = AsyncMock(return_value="<html><body>vless://proxy</body></html>")
    mock_context_manager.__aenter__.return_value = mock_response
    mock_session.get.return_value = mock_context_manager

    await fetch_from_source(mock_session, "http://example.com")
    assert "Unexpected content type for http://example.com: text/html" in caplog.text
