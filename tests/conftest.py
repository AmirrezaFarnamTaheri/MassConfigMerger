"""Pytest configuration and shared fixtures."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    src_path = str(SRC)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

from configstream.config import Settings

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
