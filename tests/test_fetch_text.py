import asyncio
import os
import sys
from aiohttp import web, ClientSession
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import aggregator_tool

pytest_plugins = "aiohttp.pytest_plugin"


@pytest.mark.asyncio
async def test_fetch_text_http_codes(aiohttp_client):
    async def ok(request):
        return web.Response(text="hi")

    async def not_found(request):
        return web.Response(status=404)

    app = web.Application()
    app.router.add_get("/ok", ok)
    app.router.add_get("/nf", not_found)
    client = await aiohttp_client(app)

    async with ClientSession() as session:
        text = await aggregator_tool.fetch_text(session, client.make_url("/ok"))
        assert text == "hi"

        text2 = await aggregator_tool.fetch_text(session, client.make_url("/nf"))
        assert text2 is None


@pytest.mark.asyncio
async def test_fetch_text_timeout(aiohttp_client):
    async def slow(request):
        await asyncio.sleep(0.05)
        return web.Response(text="late")

    app = web.Application()
    app.router.add_get("/slow", slow)
    client = await aiohttp_client(app)

    async with ClientSession() as session:
        text = await aggregator_tool.fetch_text(session, client.make_url("/slow"), timeout=0.01)
        assert text is None
