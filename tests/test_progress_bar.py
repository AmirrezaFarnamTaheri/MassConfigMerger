import asyncio
import types

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

    async with aggregator_tool.aiohttp.ClientSession() as sess:
        monkeypatch.setattr(
            aggregator_tool.aiohttp,
            "ClientSession",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not be called")),
        )
        configs = await agg.fetch_and_parse_configs(["u1", "u2"], session=sess)

    assert configs == {"vmess://cfg"}
    bar = bars[0]
    assert bar.n == 2
    assert bar.total == 2
    assert bar.closed


@pytest.mark.asyncio
async def test_signal_handler_closes_current_progress(monkeypatch):
    bars = []
    handler = {}

    class HandlerTqdm(DummyTqdm):
        def update(self, n=1):
            if not handler.get("called"):
                assert merger.current_progress is self
                handler["called"] = True
                captured["handler"]()
            super().update(n)

    def fake_tqdm(*args, **kwargs):
        bar = HandlerTqdm(*args, **kwargs)
        bars.append(bar)
        return bar

    monkeypatch.setattr("massconfigmerger.vpn_merger.tqdm", fake_tqdm)

    merger = UltimateVPNMerger()

    loop = asyncio.get_running_loop()
    captured = {}

    def fake_add_signal_handler(sig, h):
        captured["handler"] = h

    monkeypatch.setattr(loop, "add_signal_handler", fake_add_signal_handler)

    merger._register_signal_handlers()

    r1 = ConfigResult(config="a", protocol="VMess", ping_time=0.1, is_reachable=True)
    r2 = ConfigResult(config="b", protocol="VLESS", ping_time=0.2, is_reachable=True)
    merger._sort_by_performance([r1, r2])

    assert handler.get("called")
    bar = bars[0]
    assert bar.closed
    assert merger.current_progress is None


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
async def test_scrape_telegram_configs_progress(monkeypatch, tmp_path):
    bars = []

    def fake_tqdm(*args, **kwargs):
        bar = DummyTqdm(*args, **kwargs)
        bars.append(bar)
        return bar

    monkeypatch.setattr("massconfigmerger.aggregator_tool.tqdm", fake_tqdm)

    class DummyMessage:
        def __init__(self, msg):
            self.message = msg

    class DummyClient:
        def __init__(self, *a, **k):
            pass

        async def start(self):
            return self

        async def iter_messages(self, channel, offset_date=None):
            messages = [DummyMessage("vmess://direct1"), DummyMessage("http://sub.example")]
            for m in messages:
                yield m

        async def disconnect(self):
            pass

        async def connect(self):
            pass

    async def fake_fetch_text(session, url, timeout=10, *, retries=3, base_delay=1.0, **_):
        if "sub.example" in url:
            return "vmess://from_url"
        return None

    channels = tmp_path / "channels.txt"
    channels.write_text("chan1\nchan2\n")

    cfg = Settings(telegram_api_id=1, telegram_api_hash="h")

    monkeypatch.setattr(aggregator_tool, "TelegramClient", DummyClient)
    monkeypatch.setattr(aggregator_tool, "Message", DummyMessage)
    monkeypatch.setattr(aggregator_tool, "fetch_text", fake_fetch_text)
    monkeypatch.setattr(aggregator_tool, "errors", types.SimpleNamespace(RPCError=Exception))

    agg = aggregator_tool.Aggregator(cfg)
    result = await agg.scrape_telegram_configs(channels, 24)

    assert result == {"vmess://direct1", "vmess://from_url", "http://sub.example"}
    bar = bars[0]
    assert bar.n == 2
    assert bar.total == 2
    assert bar.closed
