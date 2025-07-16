import asyncio
import pytest
from massconfigmerger import aggregator_tool
from massconfigmerger.config import Settings


@pytest.mark.asyncio
async def test_aggregator_filters_with_patterns(monkeypatch, tmp_path):
    async def fake_check(*_a, **_k):
        return ["s"]

    async def fake_fetch(*_a, **_k):
        return {"trojan://pw@good.com:443", "trojan://pw@badhost:443"}

    async def fake_scrape(*_a, **_k):
        return set()

    captured = {}

    def fake_output(configs, out_dir, _cfg):
        captured["configs"] = configs
        return []

    monkeypatch.setattr(aggregator_tool.Aggregator, "check_and_update_sources", fake_check)
    monkeypatch.setattr(aggregator_tool.Aggregator, "fetch_and_parse_configs", fake_fetch)
    monkeypatch.setattr(aggregator_tool.Aggregator, "scrape_telegram_configs", fake_scrape)
    monkeypatch.setattr(aggregator_tool.Aggregator, "output_files", fake_output)

    cfg = Settings(output_dir=str(tmp_path), exclude_patterns=["bad"])
    agg = aggregator_tool.Aggregator(cfg)
    await agg.run()

    assert captured["configs"] == ["trojan://pw@good.com:443"]
