from pathlib import Path
import asyncio
import json

from massconfigmerger import aggregator_tool
from massconfigmerger.config import Settings


def test_check_and_update_sources(monkeypatch, tmp_path):
    path = tmp_path / "sources.txt"
    path.write_text("good\nbad\n")

    async def fake_fetch_text(session, url, timeout=10, *, retries=3, base_delay=1.0, **_):
        if "good" in url:
            return "vmess://test"
        return None

    monkeypatch.setattr(aggregator_tool, "fetch_text", fake_fetch_text)

    agg = aggregator_tool.Aggregator(Settings())
    async def run_test():
        async with aggregator_tool.aiohttp.ClientSession() as sess:
            monkeypatch.setattr(
                aggregator_tool.aiohttp,
                "ClientSession",
                lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not be called")),
            )
            return await agg.check_and_update_sources(path, concurrent_limit=2, session=sess)

    result = asyncio.run(run_test())
    assert result == ["good"]
    # bad should remain until failure threshold reached
    lines = path.read_text().splitlines()
    assert lines == ["good", "bad"]
    data = json.loads((tmp_path / "sources.failures.json").read_text())
    assert data["bad"] == 1


def test_prune_after_threshold(monkeypatch, tmp_path):
    path = tmp_path / "sources.txt"
    path.write_text("onlybad\n")

    async def fail_fetch(session, url, timeout=10, *, retries=3, base_delay=1.0, **_):
        return None

    monkeypatch.setattr(aggregator_tool, "fetch_text", fail_fetch)

    # first run - not pruned
    agg = aggregator_tool.Aggregator(Settings())
    asyncio.run(
        agg.check_and_update_sources(
            path,
            concurrent_limit=1,
            max_failures=2,
            disabled_path=tmp_path / "disabled.txt",
        )
    )
    assert path.read_text().splitlines() == ["onlybad"]

    # second run - should be pruned
    asyncio.run(
        agg.check_and_update_sources(
            path,
            concurrent_limit=1,
            max_failures=2,
            disabled_path=tmp_path / "disabled.txt",
        )
    )
    assert path.read_text().strip() == ""
    disabled = (tmp_path / "disabled.txt").read_text().strip().split()
    assert "onlybad" in disabled[-1]


def test_order_preserved_when_pruning(monkeypatch, tmp_path):
    path = tmp_path / "sources.txt"
    path.write_text("first\nsecond\nthird\n")

    async def fake_fetch(session, url, timeout=10, *, retries=3, base_delay=1.0, **_):
        if "second" in url:
            return None
        return "vmess://ok"

    monkeypatch.setattr(aggregator_tool, "fetch_text", fake_fetch)

    agg = aggregator_tool.Aggregator(Settings())

    async def run_test():
        async with aggregator_tool.aiohttp.ClientSession() as sess:
            monkeypatch.setattr(
                aggregator_tool.aiohttp,
                "ClientSession",
                lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not be called")),
            )
            await agg.check_and_update_sources(
                path,
                concurrent_limit=2,
                max_failures=1,
                disabled_path=tmp_path / "disabled.txt",
                session=sess,
            )

    asyncio.run(run_test())
    assert path.read_text().splitlines() == ["first", "third"]
