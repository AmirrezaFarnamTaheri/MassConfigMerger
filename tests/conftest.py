"""Pytest configuration and shared fixtures."""

import asyncio
from massconfigmerger.config import Settings

pytest_plugins = ["pytest_asyncio", "aiohttp.pytest_plugin"]

# Do not use proxies when running tests to avoid network issues with local
# test servers.
CONFIG = Settings()
CONFIG.network.http_proxy = None
CONFIG.network.socks_proxy = None
import pytest

@pytest.fixture
def loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def event_loop(loop):
    yield loop
