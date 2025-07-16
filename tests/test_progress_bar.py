import asyncio

import pytest

from massconfigmerger.vpn_merger import UltimateVPNMerger
from massconfigmerger.result_processor import ConfigResult
from massconfigmerger import aggregator_tool
from massconfigmerger.config import Settings


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

    def set_postfix(self, *args, **kwargs):
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


@pytest.mark.asyncio
async def test_fetch_and_parse_configs_progress(monkeypatch):
    bars = []

    def fake_tqdm(*args, **kwargs):
        bar = DummyTqdm(*args, **kwargs)
        bars.append(bar)
        return bar

    monkeypatch.setattr("massconfigmerger.aggregator_tool.tqdm", fake_tqdm)

    async def fake_fetch_text(*_a, **_k):
        return "vmess://cfg"

    monkeypatch.setattr("massconfigmerger.aggregator_tool.fetch_text", fake_fetch_text)

    agg = aggregator_tool.Aggregator(Settings())
    configs = await agg.fetch_and_parse_configs(["u1", "u2"])

    assert configs == {"vmess://cfg"}
    bar = bars[0]
    assert bar.n == 2
    assert bar.total == 2
    assert bar.closed


def test_sort_by_performance_progress(monkeypatch):
    bars = []

    def fake_tqdm(*args, **kwargs):
        bar = DummyTqdm(*args, **kwargs)
        bars.append(bar)
        return bar

    monkeypatch.setattr("massconfigmerger.vpn_merger.tqdm", fake_tqdm)

    merger = UltimateVPNMerger()
    r1 = ConfigResult(config="a", protocol="VMess", ping_time=0.5, is_reachable=True)
    r2 = ConfigResult(config="b", protocol="VLESS", ping_time=0.2, is_reachable=True)
    merger._sort_by_performance([r1, r2])

    bar = bars[0]
    assert bar.n == 2
    assert bar.total == 2
    assert bar.closed
