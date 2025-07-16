"""Pytest configuration and shared fixtures."""

import importlib
import sys

try:
    importlib.import_module("pytest_asyncio")
except ModuleNotFoundError as exc:  # pragma: no cover - only triggers when deps missing
    message = (
        "pytest_asyncio is required. Install dev dependencies with 'pip install -e .[dev]' "
        "or 'pip install -r requirements-dev.txt'."
    )
    print(message, file=sys.stderr)
    raise RuntimeError(message) from exc

pytest_plugins = ["pytest_asyncio", "aiohttp.pytest_plugin"]

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
