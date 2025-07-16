import asyncio

import pytest

from massconfigmerger.vpn_merger import UltimateVPNMerger
from massconfigmerger.result_processor import ConfigResult
from massconfigmerger import aggregator_tool


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

    configs = await aggregator_tool.fetch_and_parse_configs(["u1", "u2"])

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


@pytest.mark.asyncio
async def test_run_pipeline_summary(monkeypatch, tmp_path, capsys):
    cfg = aggregator_tool.Settings(
        output_dir=str(tmp_path / "o"),
        log_dir=str(tmp_path / "l"),
        write_base64=False,
        write_singbox=False,
        write_clash=False,
    )

    async def fake_check(*_a, **_k):
        aggregator_tool.STATS["sources_checked"] = 3
        return ["a", "b"]

    async def fake_fetch(*_a, **_k):
        return {"vmess://a", "vmess://b"}

    async def fake_scrape(*_a, **_k):
        return set()

    monkeypatch.setattr(aggregator_tool, "check_and_update_sources", fake_check)
    monkeypatch.setattr(aggregator_tool, "fetch_and_parse_configs", fake_fetch)
    monkeypatch.setattr(aggregator_tool, "scrape_telegram_configs", fake_scrape)
    monkeypatch.setattr(aggregator_tool, "deduplicate_and_filter", lambda c, *_: list(c))
    monkeypatch.setattr(aggregator_tool, "output_files", lambda c, out, cfg: [out / "m.txt"])

    await aggregator_tool.run_pipeline(cfg, sources_file=tmp_path / "s.txt", channels_file=tmp_path / "c.txt")
    captured = capsys.readouterr().out
    assert "Sources checked: 3" in captured


@pytest.mark.asyncio
async def test_vpn_merger_summary(monkeypatch, capsys):
    merger = UltimateVPNMerger()

    async def fake_test():
        return ["u1"]

    async def fake_fetch(_):
        merger.all_results = [
            ConfigResult(config="vmess://a", protocol="VMess", source_url="u1"),
            ConfigResult(config="vmess://b", protocol="VMess", source_url="u1"),
        ]

    async def fake_preflight(*_a, **_k):
        return True

    monkeypatch.setattr(merger, "_test_and_filter_sources", fake_test)
    monkeypatch.setattr(merger, "_fetch_all_sources", fake_fetch)
    monkeypatch.setattr(merger, "_preflight_connectivity_check", fake_preflight)
    monkeypatch.setattr(merger, "_sort_by_performance", lambda x: x)

    async def noop_async(*_a, **_k):
        return None

    monkeypatch.setattr(merger, "_generate_comprehensive_outputs", noop_async)
    monkeypatch.setattr(merger, "_save_proxy_history", noop_async)
    monkeypatch.setattr(merger, "_print_final_summary", lambda *a, **k: None)
    monkeypatch.setattr(merger.processor.tester, "close", noop_async)

    await merger.run()
    captured = capsys.readouterr().out
    assert "Sources checked:" in captured
