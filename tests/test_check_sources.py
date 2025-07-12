import os
import sys
from pathlib import Path
import asyncio
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import aggregator_tool


def test_check_and_update_sources(monkeypatch, tmp_path):
    path = tmp_path / "sources.txt"
    path.write_text("good\nbad\n")

    async def fake_fetch_text(session, url, timeout=10):
        if "good" in url:
            return "vmess://test"
        return None

    monkeypatch.setattr(aggregator_tool, "fetch_text", fake_fetch_text)

    result = asyncio.run(
        aggregator_tool.check_and_update_sources(path, concurrent_limit=2)
    )
    assert result == ["good"]
    # bad should remain until failure threshold reached
    lines = path.read_text().splitlines()
    assert set(lines) == {"good", "bad"}
    data = json.loads((tmp_path / "sources.failures.json").read_text())
    assert data["bad"] == 1


def test_prune_after_threshold(monkeypatch, tmp_path):
    path = tmp_path / "sources.txt"
    path.write_text("onlybad\n")

    async def fail_fetch(session, url, timeout=10):
        return None

    monkeypatch.setattr(aggregator_tool, "fetch_text", fail_fetch)

    # first run - not pruned
    asyncio.run(
        aggregator_tool.check_and_update_sources(
            path,
            concurrent_limit=1,
            max_failures=2,
            disabled_path=tmp_path / "disabled.txt",
        )
    )
    assert path.read_text().splitlines() == ["onlybad"]

    # second run - should be pruned
    asyncio.run(
        aggregator_tool.check_and_update_sources(
            path,
            concurrent_limit=1,
            max_failures=2,
            disabled_path=tmp_path / "disabled.txt",
        )
    )
    assert path.read_text().strip() == ""
    disabled = (tmp_path / "disabled.txt").read_text().strip().split()
    assert "onlybad" in disabled[-1]
