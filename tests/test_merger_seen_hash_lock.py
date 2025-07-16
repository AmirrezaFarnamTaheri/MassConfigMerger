import asyncio
import pytest
from aiohttp import web

from massconfigmerger.vpn_merger import UltimateVPNMerger

pytest_plugins = "aiohttp.pytest_plugin"


@pytest.mark.asyncio
async def test_merger_seen_hash_lock_prevents_duplicates():
    async def handler(request):
        return web.Response(text="vmess://abcdef0123456789abc")

    app = web.Application()
    app.router.add_get("/", handler)
    from aiohttp.test_utils import TestServer, TestClient

    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()

    merger = UltimateVPNMerger()
    await merger.fetcher.close()
    merger.fetcher.session = client.session
    merger.fetcher._own_session = False

    url = str(client.make_url("/"))
    r1, r2 = await asyncio.gather(
        merger.fetcher.fetch_source(url),
        merger.fetcher.fetch_source(url),
    )
    await client.close()

    total = len(r1[1]) + len(r2[1])
    assert total == 1
    assert len(merger.seen_hashes) == 1
