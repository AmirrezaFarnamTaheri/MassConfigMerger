"""Pytest configuration and shared fixtures."""

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import importlib
import importlib.util

import pytest

from configstream.config import Settings


def _load_optional_plugin(name: str) -> Optional[str]:
    """Try to load an optional pytest plugin.

    When running in the execution environment used for these kata style tasks the
    optional test dependencies are often not installed. Importing a missing
    plugin would therefore raise an exception during pytest collection and no
    tests would be executed.  To keep the suite runnable we attempt the import
    dynamically and only register the plugin when it is available locally.
    """

    if importlib.util.find_spec(name) is None:
        return None
    importlib.import_module(name)
    return name


# Ensure optional pytest plugins are loaded when available without failing when
# they are missing from the execution environment.
pytest_plugins = [
    plugin
    for plugin in (
        _load_optional_plugin("pytest_asyncio"),
        _load_optional_plugin("aiohttp.pytest_plugin"),
    )
    if plugin is not None
]


def pytest_addoption(parser):
    """Register compatibility ini options when pytest-asyncio is unavailable."""

    parser.addini("asyncio_mode", "Compatibility shim for pytest-asyncio", default="auto")


# Do not use proxies when running tests to avoid network issues with local
# test servers.
CONFIG = Settings()
CONFIG.network.http_proxy = None
CONFIG.network.socks_proxy = None

@pytest.fixture
def loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def event_loop(loop):
    yield loop