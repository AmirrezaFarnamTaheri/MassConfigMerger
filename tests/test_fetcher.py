import asyncio

import pytest
from aiohttp import web

from configstream.fetcher import fetch_from_source


@pytest.mark.asyncio
async def test_fetch_from_source_success(aiohttp_client):
    """Test successful fetching from a source."""

    async def handler(request):
        return web.Response(text="proxy1\nproxy2\n#comment\nproxy3")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    source_url = str(client.server.make_url("/"))
    async with client.session as session:
        result = await fetch_from_source(session, source_url)

    assert result.success is True
    assert result.configs == ["proxy1", "proxy2", "proxy3"]
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_fetch_from_source_http_error(aiohttp_client):
    """Test fetch with an HTTP error."""

    async def handler(request):
        return web.Response(status=500, text="Internal Server Error")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    source_url = str(client.server.make_url("/"))
    async with client.session as session:
        result = await fetch_from_source(session, source_url)

    assert result.success is False
    assert result.configs == []
    assert "Server error: 500" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_timeout(aiohttp_client):
    """Test fetch with a timeout."""

    async def handler(request):
        await asyncio.sleep(2)
        return web.Response(text="proxy1")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    source_url = str(client.server.make_url("/"))
    async with client.session as session:
        result = await fetch_from_source(session, source_url, timeout=1)

    assert result.success is False
    assert result.configs == []
    assert "Timeout" in result.error


@pytest.mark.asyncio
async def test_fetch_from_source_empty_source(aiohttp_client):
    """Test fetching from an empty source."""

    async def handler(request):
        return web.Response(text="")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    source_url = str(client.server.make_url("/"))
    async with client.session as session:
        result = await fetch_from_source(session, source_url)

    assert result.success is True
    assert result.configs == []
    assert result.status_code == 200