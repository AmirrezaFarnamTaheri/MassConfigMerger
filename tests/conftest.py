"""Test configuration and helper fixtures."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, List

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


@pytest.hookimpl
def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers used in the test-suite."""

    config.addinivalue_line("markers", "asyncio: run the test inside an event loop")


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Execute ``async def`` tests marked with ``@pytest.mark.asyncio``."""

    test_func = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_func):
        return None

    if pyfuncitem.get_closest_marker("asyncio") is None:
        return None

    fixture_names = pyfuncitem._fixtureinfo.argnames  # type: ignore[attr-defined]
    call_kwargs = {name: pyfuncitem.funcargs[name] for name in fixture_names}
    asyncio.run(test_func(**call_kwargs))
    return True


@dataclass
class SimpleFS:
    """Lightweight fake file-system helper used by CLI tests."""

    root: Path

    def create_file(self, relative_path: str, contents: str = "") -> Path:
        file_path = self.root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(contents)
        return file_path


@pytest.fixture
def fs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleFS:
    """Provide a simple fake file-system rooted at ``tmp_path``."""

    original_cwd = Path.cwd()
    monkeypatch.chdir(tmp_path)
    helper = SimpleFS(tmp_path)

    yield helper

    monkeypatch.chdir(original_cwd)


@pytest.fixture
def aiohttp_client(
    request: pytest.FixtureRequest,
) -> Callable[[web.Application], Awaitable[TestClient]]:
    """Create an ``aiohttp`` test client without external pytest plugins."""

    active_clients: List[TestClient] = []
    active_servers: List[TestServer] = []

    async def factory(app: web.Application) -> TestClient:
        server = TestServer(app)
        await server.start_server()
        client = TestClient(server)
        await client.start_server()
        active_servers.append(server)
        active_clients.append(client)
        return client

    async def finalize() -> None:
        for client in active_clients:
            await client.close()
        for server in active_servers:
            await server.close()

    def cleanup() -> None:
        if active_clients or active_servers:
            asyncio.run(finalize())

    request.addfinalizer(cleanup)
    return factory
