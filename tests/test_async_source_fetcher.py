import asyncio
import os
import sys
import pytest

pytest_plugins = "aiohttp.pytest_plugin"

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from vpn_merger import AsyncSourceFetcher, EnhancedConfigProcessor
from massconfigmerger.config import settings as CONFIG
from aiohttp import web


@pytest.mark.asyncio
async def test_fetch_source_retries_on_error(aiohttp_client, monkeypatch):
    counter = {"calls": 0}

    async def handler(request):
        counter["calls"] += 1
        if counter["calls"] < 2:
            return web.Response(status=500)
        return web.Response(text="vmess://0123456789abcdef01234")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    fetcher = AsyncSourceFetcher(EnhancedConfigProcessor(), set())
    fetcher.session = client.session

    monkeypatch.setattr(CONFIG, "max_retries", 3)
    url, results = await fetcher.fetch_source(client.make_url("/"))

    assert counter["calls"] >= 2
    assert len(results) == 1
    assert results[0].config == "vmess://0123456789abcdef01234"


@pytest.mark.asyncio
async def test_fetch_source_timeout(aiohttp_client, monkeypatch):
    async def handler(request):
        await asyncio.sleep(0.1)
        return web.Response(text="vmess://lateconfig012345")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    fetcher = AsyncSourceFetcher(EnhancedConfigProcessor(), set())
    fetcher.session = client.session

    monkeypatch.setattr(CONFIG, "request_timeout", 0.01)
    monkeypatch.setattr(CONFIG, "max_retries", 1)
    url, results = await fetcher.fetch_source(client.make_url("/"))

    assert results == []


@pytest.mark.asyncio
async def test_fetcher_lock_serializes_requests(aiohttp_client):
    concurrency = 0
    max_conc = 0

    async def handler(request):
        nonlocal concurrency, max_conc
        concurrency += 1
        max_conc = max(max_conc, concurrency)
        await asyncio.sleep(0.05)
        concurrency -= 1
        return web.Response(text="vmess://abcdef0123456789abc")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    fetcher = AsyncSourceFetcher(EnhancedConfigProcessor(), set())
    fetcher.session = client.session

    await asyncio.gather(
        fetcher.fetch_source(client.make_url("/")),
        fetcher.fetch_source(client.make_url("/")),
    )

    assert max_conc == 1
