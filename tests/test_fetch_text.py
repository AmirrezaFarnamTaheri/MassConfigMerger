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
            return web.Response(status=503)
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    text = await aggregator_tool.fetch_text(client.session, str(client.make_url("/")))
    assert counter["calls"] >= 2
    assert text == "ok"


@pytest.mark.asyncio
async def test_fetch_text_retryable_429(aiohttp_client):
    counter = {"calls": 0}

    async def handler(request):
        counter["calls"] += 1
        if counter["calls"] < 2:
            return web.Response(status=429)
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


@pytest.mark.asyncio
async def test_fetch_text_backoff(monkeypatch, aiohttp_client):
    """Ensure exponential backoff between retries."""
    delays = []

    async def fake_sleep(d):
        delays.append(d)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(aggregator_tool.random, "uniform", lambda a, b: 0)

    async def handler(request):
        return web.Response(status=500)

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    text = await aggregator_tool.fetch_text(
        client.session, str(client.make_url("/")), timeout=0.01
    )

    assert text is None
    assert delays == [1.0, 2.0]


@pytest.mark.asyncio
async def test_fetch_text_timeout(aiohttp_client):
    async def handler(request):
        await asyncio.sleep(0.1)
        return web.Response(text="late")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    text = await aggregator_tool.fetch_text(
        client.session,
        str(client.make_url("/")),
        timeout=0.01,
        retries=1,
    )

    assert text is None


class DummyResponse:
    def __init__(self, status, text="ok"):
        self.status = status
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def text(self):
        return self._text


class DummySession:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = 0

    def get(self, url, timeout=None):
        status = self.statuses[min(self.calls, len(self.statuses) - 1)]
        self.calls += 1
        return DummyResponse(status)


@pytest.mark.asyncio
async def test_fetch_text_mock_404_no_retry():
    session = DummySession([404])
    text = await aggregator_tool.fetch_text(session, "http://example")
    assert text is None
    assert session.calls == 1


@pytest.mark.asyncio
async def test_fetch_text_mock_503_retry():
    session = DummySession([503, 200])
    text = await aggregator_tool.fetch_text(session, "http://example")
    assert text == "ok"
    assert session.calls == 2
