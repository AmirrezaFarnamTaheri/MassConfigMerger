pytest_plugins = ["pytest_asyncio", 'aiohttp.pytest_plugin']

import asyncio
import os
import pytest

@pytest.fixture
def loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def event_loop(loop):
    yield loop


@pytest.fixture(autouse=True)
def clear_proxy_env(monkeypatch):
    for var in ["HTTP_PROXY", "http_proxy", "SOCKS_PROXY", "socks_proxy"]:
        monkeypatch.delenv(var, raising=False)
    try:
        from massconfigmerger.vpn_merger import CONFIG
        CONFIG.http_proxy = None
        CONFIG.socks_proxy = None
        print("clear_proxy_env applied")
    except Exception:
        pass
