import asyncio
import pytest

pytest_plugins = "aiohttp.pytest_plugin"

from massconfigmerger.source_fetcher import AsyncSourceFetcher
from massconfigmerger.result_processor import EnhancedConfigProcessor, CONFIG
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
async def test_seen_hash_lock_prevents_duplicates(aiohttp_client):
    async def handler(request):
        return web.Response(text="vmess://abcdef0123456789abc")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    seen = set()
    fetcher = AsyncSourceFetcher(EnhancedConfigProcessor(), seen)
    fetcher.session = client.session

    r1, r2 = await asyncio.gather(
        fetcher.fetch_source(client.make_url("/")),
        fetcher.fetch_source(client.make_url("/")),
    )

    total = len(r1[1]) + len(r2[1])
    assert total == 1


@pytest.mark.asyncio
async def test_shared_lock_across_instances(aiohttp_client):
    async def handler(request):
        return web.Response(text="vmess://abcdef0123456789abc")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    seen = set()
    lock = asyncio.Lock()
    f1 = AsyncSourceFetcher(EnhancedConfigProcessor(), seen, lock)
    f2 = AsyncSourceFetcher(EnhancedConfigProcessor(), seen, lock)
    f1.session = client.session
    f2.session = client.session

    r1, r2 = await asyncio.gather(
        f1.fetch_source(client.make_url("/")),
        f2.fetch_source(client.make_url("/")),
    )

    total = len(r1[1]) + len(r2[1])
    assert total == 1


@pytest.mark.asyncio
async def test_fetch_source_concurrent_execution(aiohttp_client):
    async def handler(request):
        await asyncio.sleep(0.1)
        return web.Response(text="vmess://abcdef0123456789abc")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    fetcher = AsyncSourceFetcher(EnhancedConfigProcessor(), set())
    fetcher.session = client.session

    start = asyncio.get_event_loop().time()
    await asyncio.gather(
        fetcher.fetch_source(client.make_url("/")),
        fetcher.fetch_source(client.make_url("/")),
    )
    elapsed = asyncio.get_event_loop().time() - start

    assert elapsed < 0.15


@pytest.mark.asyncio
async def test_source_availability_concurrent_execution(aiohttp_client):
    async def handler(request):
        await asyncio.sleep(0.1)
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    fetcher = AsyncSourceFetcher(EnhancedConfigProcessor(), set())
    fetcher.session = client.session

    start = asyncio.get_event_loop().time()
    await asyncio.gather(
        fetcher.test_source_availability(client.make_url("/")),
        fetcher.test_source_availability(client.make_url("/")),
    )
    elapsed = asyncio.get_event_loop().time() - start

    assert elapsed < 0.15
