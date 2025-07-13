pytest_plugins = ["pytest_asyncio", 'aiohttp.pytest_plugin']

import asyncio
import pytest

@pytest.fixture
def loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def event_loop(loop):
    yield loop
