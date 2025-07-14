import asyncio

import pytest

from massconfigmerger.vpn_merger import UltimateVPNMerger
from massconfigmerger.result_processor import ConfigResult


class DummyTqdm:
    def __init__(self, *args, **kwargs):
        self.total = kwargs.get("total", None)
        self.desc = kwargs.get("desc")
        self.unit = kwargs.get("unit")
        self.n = 0
        self.closed = False

    def update(self, n=1):
        self.n += n

    def refresh(self):
        pass

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_fetch_all_sources_updates_progress(monkeypatch):
    bars = []

    def fake_tqdm(*args, **kwargs):
        bar = DummyTqdm(*args, **kwargs)
        bars.append(bar)
        return bar

    monkeypatch.setattr("massconfigmerger.vpn_merger.tqdm", fake_tqdm)

    merger = UltimateVPNMerger()

    async def fake_fetch(url):
        results = [
            ConfigResult(config="vmess://a", protocol="VMess", host="h", port=80, source_url=url),
            ConfigResult(config="vmess://b", protocol="VMess", host="h", port=80, source_url=url),
        ]
        if merger.fetcher.progress:
            merger.fetcher.progress.total += len(results)
            merger.fetcher.progress.refresh()
            for _ in results:
                merger.fetcher.progress.update(1)
        return url, results

    monkeypatch.setattr(merger.fetcher, "fetch_source", fake_fetch)

    await merger._fetch_all_sources(["u1", "u2"])

    bar = bars[0]
    assert bar.n == 4
    assert bar.closed
