import os
import sys
import asyncio
import pytest
from aiohttp import web

pytest_plugins = "aiohttp.pytest_plugin"

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import aggregator_tool


@pytest.mark.asyncio
async def test_fetch_text_success(aiohttp_client):
    async def handler(request):
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    text = await aggregator_tool.fetch_text(client.session, str(client.make_url("/")))
    assert text == "ok"


@pytest.mark.asyncio
async def test_fetch_text_retryable(aiohttp_client):
    counter = {"calls": 0}

    async def handler(request):
        counter["calls"] += 1
        if counter["calls"] < 2:
            return web.Response(status=500)
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    text = await aggregator_tool.fetch_text(client.session, str(client.make_url("/")))
    assert counter["calls"] >= 2
    assert text == "ok"


@pytest.mark.asyncio
async def test_fetch_text_non_retryable(aiohttp_client):
    async def handler(request):
        return web.Response(status=404)

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    text = await aggregator_tool.fetch_text(client.session, str(client.make_url("/")))
    assert text is None

    text = await aggregator_tool.fetch_text(client.session, "not a url")
    assert text is None

