import asyncio
import pytest
from aiohttp import web

pytest_plugins = "aiohttp.pytest_plugin"

from massconfigmerger import aggregator_tool
from massconfigmerger.config import Settings
from massconfigmerger.vpn_merger import UltimateVPNMerger
from massconfigmerger.result_processor import ConfigResult, CONFIG
from massconfigmerger.config import Settings


@pytest.mark.asyncio
async def test_fetch_and_parse_configs_handles_errors(aiohttp_client, tmp_path):
    async def good(request):
        return web.Response(text="vmess://good")

    async def bad(request):
        return web.Response(status=500)

    async def slow(request):
        await asyncio.sleep(0.1)
        return web.Response(text="vmess://slow")

    app = web.Application()
    app.router.add_get("/good", good)
    app.router.add_get("/bad", bad)
    app.router.add_get("/slow", slow)
    client = await aiohttp_client(app)

    urls = [
        str(client.make_url("/good")),
        str(client.make_url("/bad")),
        str(client.make_url("/slow")),
    ]

    agg = aggregator_tool.Aggregator(Settings())
    configs = await agg.fetch_and_parse_configs(
        urls, concurrent_limit=3, request_timeout=0.05
    )
    assert configs == {"vmess://good"}

    path = tmp_path / "sources.txt"
    path.write_text("\n".join(urls))
    valid = await agg.check_and_update_sources(
        path, concurrent_limit=3, request_timeout=0.05, prune=False
    )
    assert valid == [str(client.make_url("/good"))]


@pytest.mark.asyncio
async def test_file_lock_prevents_duplicates(tmp_path, monkeypatch):
    monkeypatch.setattr(CONFIG, "output_dir", str(tmp_path))
    for attr in ("write_base64", "write_clash", "write_clash_proxies", "write_csv"):
        monkeypatch.setattr(CONFIG, attr, False)
    merger = UltimateVPNMerger()

    res = ConfigResult(
        config="vmess://uuid@host:80",
        protocol="VMess",
        host="host",
        port=80,
        ping_time=0.1,
        is_reachable=True,
        source_url="s",
    )
    stats = merger._analyze_results([res], [])

    active = 0
    original = UltimateVPNMerger._generate_comprehensive_outputs

    async def wrapped(self, *a, **k):
        nonlocal active
        active += 1
        assert active == 1
        try:
            return await original(self, *a, **k)
        finally:
            active -= 1

    monkeypatch.setattr(UltimateVPNMerger, "_generate_comprehensive_outputs", wrapped)

    await asyncio.gather(
        merger._generate_comprehensive_outputs([res], stats, 0.0),
        merger._generate_comprehensive_outputs([res], stats, 0.0),
    )

    assert (tmp_path / "vpn_subscription_raw.txt").exists()
    assert not any(p.suffix == ".tmp" for p in tmp_path.iterdir())


@pytest.mark.asyncio
async def test_aggregator_output_files_atomic(tmp_path):
    cfg = Settings(
        output_dir=str(tmp_path),
        write_base64=False,
        write_singbox=False,
        write_clash=False,
    )
    aggregator_tool.Aggregator.output_files(["vmess://uuid@host:80"], tmp_path, cfg)

    assert (tmp_path / "vpn_subscription_raw.txt").exists()
    assert not any(p.suffix == ".tmp" for p in tmp_path.iterdir())


@pytest.mark.asyncio
async def test_run_pipeline_prunes_bad_sources(aiohttp_client, tmp_path, monkeypatch):
    async def good(request):
        return web.Response(text="vless://user@host:80")

    async def bad(request):
        return web.Response(status=500)

    app = web.Application()
    app.router.add_get("/good", good)
    app.router.add_get("/bad", bad)
    client = await aiohttp_client(app)

    src = tmp_path / "sources.txt"
    src.write_text(f"{client.make_url('/good')}\n{client.make_url('/bad')}\n")
    channels = tmp_path / "channels.txt"
    channels.write_text("")

    cfg = Settings(
        output_dir=str(tmp_path / "out"),
        log_dir=str(tmp_path / "log"),
        write_base64=False,
        write_singbox=False,
        write_clash=False,
        concurrent_limit=2,
        request_timeout=1,
        retry_attempts=1,
    )

    async def fake_scrape(*_a, **_k):
        return set()

    monkeypatch.setattr(aggregator_tool.Aggregator, "scrape_telegram_configs", fake_scrape)

    agg = aggregator_tool.Aggregator(cfg)
    out_dir, _ = await agg.run(
        None,
        sources_file=src,
        channels_file=channels,
        last_hours=24,
        failure_threshold=1,
    )

    merged = out_dir / "vpn_subscription_raw.txt"
    assert merged.exists()
