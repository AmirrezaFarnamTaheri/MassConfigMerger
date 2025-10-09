"""Pytest configuration and shared fixtures."""

from configstream.config import Settings
import pytest
import importlib.util
import importlib
import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Optional
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def _load_optional_plugin(name: str) -> Optional[str]:
    """Try to load an optional pytest plugin."""
    if importlib.util.find_spec(name) is None:
        return None
    importlib.import_module(name)
    return name


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
    parser.addini("asyncio_mode",
                  "Compatibility shim for pytest-asyncio", default="auto")


@pytest.fixture
def loop():
    """Provide a new event loop for each test function."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def event_loop(loop):
    """Ensure tests run in the correct event loop."""
    yield loop


@pytest.fixture
def settings(fs) -> Settings:
    """Create a Settings object with a relative output directory in the fake FS."""
    output_dir_name = "test_output"
    fs.create_dir(output_dir_name)
    fs.create_file(
        "config.yaml", contents=f"output:\n  output_dir: {output_dir_name}")

    settings_obj = Settings(
        output={"output_dir": output_dir_name},
        security={"web_api_token": "test-token"},
        config_file=Path("config.yaml"),
    )

    sources_file_path = Path(settings_obj.sources.sources_file)
    if not fs.exists(sources_file_path):
        fs.create_file(sources_file_path, create_missing_dirs=True)

    return settings_obj


@pytest.fixture
def app(fs, settings):
    """Create and configure a new app instance for each test."""
    from configstream.web_dashboard import create_app

    fs.add_real_directory(str(Path(SRC_PATH, "configstream", "templates")))

    app_instance = create_app(settings=settings)
    app_instance.config.update({"TESTING": True})

    def _get_werkzeug_version() -> str:
        return "3.0.3"

    from flask import testing
    original_get_version = testing._get_werkzeug_version
    testing._get_werkzeug_version = _get_werkzeug_version

    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from prometheus_client import make_wsgi_app
    app_instance.wsgi_app = DispatcherMiddleware(
        app_instance.wsgi_app, {"/metrics": make_wsgi_app()})

    yield app_instance

    testing._get_werkzeug_version = original_get_version


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()
