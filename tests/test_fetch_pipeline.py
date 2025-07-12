import asyncio
import os
import sys
from aiohttp import web
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import aggregator_tool

pytest_plugins = "aiohttp.pytest_plugin"


@pytest.mark.asyncio
async def test_fetch_and_parse_configs_mixed(aiohttp_client):
    async def good1(request):
        return web.Response(text="vmess://good1")

    async def good2(request):
        encoded = "vmess://good2".encode()
        return web.Response(body=encoded)

    async def empty(request):
        return web.Response(text="")

    async def bad(request):
        return web.Response(status=500)

    async def slow(request):
        await asyncio.sleep(0.05)
        return web.Response(text="vmess://slow")

    app = web.Application()
    app.router.add_get("/good1", good1)
    app.router.add_get("/good2", good2)
    app.router.add_get("/empty", empty)
    app.router.add_get("/bad", bad)
    app.router.add_get("/slow", slow)
    client = await aiohttp_client(app)

    urls = [
        client.make_url("/good1"),
        client.make_url("/good2"),
        client.make_url("/empty"),
        client.make_url("/bad"),
        client.make_url("/slow"),
    ]

    configs = await aggregator_tool.fetch_and_parse_configs(urls, max_concurrent=3, request_timeout=0.01)
    assert configs == {"vmess://good1", "vmess://good2"}
