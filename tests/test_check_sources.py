import os
import sys
from pathlib import Path
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import aggregator_tool


def test_check_and_update_sources(monkeypatch, tmp_path):
    path = tmp_path / "sources.txt"
    path.write_text("good\nbad\n")

    async def fake_fetch_text(session, url):
        if "good" in url:
            return "vmess://test"
        return None

    monkeypatch.setattr(aggregator_tool, "fetch_text", fake_fetch_text)

    result = asyncio.run(aggregator_tool.check_and_update_sources(path, concurrent_limit=2))
    assert result == ["good"]
