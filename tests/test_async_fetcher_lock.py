import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from vpn_merger import AsyncSourceFetcher, EnhancedConfigProcessor, CONFIG


class DummyResponse:
    def __init__(self, text):
        self.status = 200
        self._text = text

    async def __aenter__(self):
        await asyncio.sleep(0.01)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def text(self):
        await asyncio.sleep(0.01)
        return self._text


class DummySession:
    def __init__(self, text):
        self._text = text

    def get(self, url, headers=None, timeout=None):
        return DummyResponse(self._text)


async def run_fetcher():
    processor = EnhancedConfigProcessor()
    seen = set()
    fetcher = AsyncSourceFetcher(processor, seen)
    text = "trojan://pw@host:443?notes=abc\n" * 2
    fetcher.session = DummySession(text)
    CONFIG.enable_url_testing = False
    res1, res2 = await asyncio.gather(
        fetcher.fetch_source("u1"),
        fetcher.fetch_source("u2"),
    )
    all_configs = [r.config for _, results in (res1, res2) for r in results]
    return all_configs, seen


def test_fetcher_lock():
    configs, seen = asyncio.run(run_fetcher())
    assert len(configs) == 1
    assert len(seen) == 1
