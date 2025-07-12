import os
import sys
from pathlib import Path
import asyncio
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import aggregator_tool


def test_check_and_update_sources_threshold(monkeypatch, tmp_path):
    path = tmp_path / "sources.txt"
    path.write_text("good\nbad\n")

    async def fake_fetch_text(session, url):
        return "vmess://test" if "good" in url else None

    monkeypatch.setattr(aggregator_tool, "fetch_text", fake_fetch_text)

    result1 = asyncio.run(
        aggregator_tool.check_and_update_sources(
            path, concurrent_limit=2, failure_limit=2
        )
    )
    assert sorted(result1) == ["bad", "good"]
    fails = json.load(open(path.with_name("sources_failures.json")))
    assert fails == {"bad": 1}

    result2 = asyncio.run(
        aggregator_tool.check_and_update_sources(
            path, concurrent_limit=2, failure_limit=2
        )
    )
    assert result2 == ["good"]
    fails2 = json.load(open(path.with_name("sources_failures.json")))
    assert fails2 == {}
    removed = path.with_name("sources_removed.txt").read_text().strip().splitlines()
    assert removed == ["bad"]
