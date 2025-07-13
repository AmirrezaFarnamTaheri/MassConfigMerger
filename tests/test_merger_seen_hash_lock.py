import asyncio
import os
import sys
import pytest
from aiohttp import web

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from vpn_merger import UltimateVPNMerger

pytest_plugins = "aiohttp.pytest_plugin"


@pytest.mark.asyncio
async def test_merger_seen_hash_lock_prevents_duplicates(aiohttp_client):
    async def handler(request):
        return web.Response(text="vmess://abcdef0123456789abc")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    merger = UltimateVPNMerger()
    merger.fetcher.session = client.session

    r1, r2 = await asyncio.gather(
        merger.fetcher.fetch_source(client.make_url("/")),
        merger.fetcher.fetch_source(client.make_url("/")),
    )

    total = len(r1[1]) + len(r2[1])
    assert total == 1
    assert len(merger.seen_hashes) == 1
