"""Pytest configuration and shared fixtures."""

import importlib
import sys

try:
    importlib.import_module("pytest_asyncio")
except ModuleNotFoundError as exc:  # pragma: no cover - only triggers when deps missing
    message = (
        "Missing required plugin 'pytest_asyncio'.\n"
        "Install the development dependencies first:\n"
        "  pip install -e .[dev]\n"
        "  # or\n"
        "  pip install -r requirements-dev.txt"
    )
    print(message, file=sys.stderr)
    raise RuntimeError(message) from exc

pytest_plugins = ["pytest_asyncio", "aiohttp.pytest_plugin"]

import asyncio
from massconfigmerger.result_processor import CONFIG

# Do not use proxies when running tests to avoid network issues with local
# test servers.
CONFIG.HTTP_PROXY = None
CONFIG.SOCKS_PROXY = None
import pytest

@pytest.fixture
def loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def event_loop(loop):
    yield loop
