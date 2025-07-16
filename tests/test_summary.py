import pytest

from massconfigmerger import aggregator_tool
from massconfigmerger.vpn_merger import UltimateVPNMerger
from massconfigmerger.result_processor import ConfigResult
from massconfigmerger.config import Settings


@pytest.mark.asyncio
async def test_run_pipeline_prints_summary(monkeypatch, capsys, tmp_path):
    async def fake_check(*_a, **_k):
        return ["s1", "s2"]

    async def fake_fetch(*_a, **_k):
        return {"vmess://a", "vmess://b"}

    async def fake_scrape(*_a, **_k):
        return set()

    def fake_output(configs, out_dir, cfg):
        return [out_dir / "merged.txt"]

    def fake_dedup(configs, _cfg, _p):
        return list(configs)

    monkeypatch.setattr(aggregator_tool, "check_and_update_sources", fake_check)
    monkeypatch.setattr(aggregator_tool, "fetch_and_parse_configs", fake_fetch)
    monkeypatch.setattr(aggregator_tool, "scrape_telegram_configs", fake_scrape)
    monkeypatch.setattr(aggregator_tool, "output_files", fake_output)
    monkeypatch.setattr(aggregator_tool, "deduplicate_and_filter", fake_dedup)

    await aggregator_tool.run_pipeline(Settings(output_dir=str(tmp_path)))
    out = capsys.readouterr().out
    assert "Sources checked: 2" in out
    assert "Configs fetched: 2" in out
    assert "Unique configs: 2" in out


@pytest.mark.asyncio
async def test_vpn_merger_run_summary(monkeypatch, capsys):
    merger = UltimateVPNMerger()
    merger.sources = ["s1", "s2"]

    async def fake_test():
        return ["s1", "s2"]

    async def fake_fetch_all(sources):
        merger.all_results.extend([
            ConfigResult(config="vmess://a", protocol="VMess", host="h", port=80, source_url="s1"),
            ConfigResult(config="vmess://b", protocol="VMess", host="h", port=80, source_url="s2"),
        ])
        return merger.all_results

    monkeypatch.setattr(merger, "_test_and_filter_sources", fake_test)
    async def fake_preflight(*_a, **_k):
        return True

    monkeypatch.setattr(merger, "_preflight_connectivity_check", fake_preflight)
    monkeypatch.setattr(merger, "_fetch_all_sources", fake_fetch_all)

    from massconfigmerger.result_processor import CONFIG
    monkeypatch.setattr(CONFIG, "enable_url_testing", False)
    monkeypatch.setattr(CONFIG, "enable_sorting", False)

    monkeypatch.setattr(merger, "_deduplicate_config_results", lambda r: r)
    monkeypatch.setattr(merger, "_sort_by_performance", lambda r: r)

    async def fake_generate(*_a, **_k):
        return None

    async def fake_save(*_a, **_k):
        return None

    monkeypatch.setattr(merger, "_generate_comprehensive_outputs", fake_generate)
    monkeypatch.setattr(merger, "_save_proxy_history", fake_save)
    monkeypatch.setattr(merger, "_print_final_summary", lambda *a, **k: None)

    async def fake_load(*_a, **_k):
        return []

    monkeypatch.setattr(merger, "_load_existing_results", fake_load)

    await merger.run()
    out = capsys.readouterr().out
    assert "Sources checked: 2" in out
    assert "Configs fetched: 2" in out
    assert "Unique configs: 2" in out
