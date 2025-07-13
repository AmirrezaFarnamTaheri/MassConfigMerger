import asyncio
import json
from pathlib import Path

from massconfigmerger.vpn_merger import UltimateVPNMerger, CONFIG


def test_proxy_history_update(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    merger = UltimateVPNMerger()
    h = merger.processor.create_semantic_hash("vmess://id@h:80")
    asyncio.run(merger._update_history(h, True, 0.123))
    asyncio.run(merger._save_proxy_history())
    data = json.loads(merger.history_path.read_text())
    assert data[h]["successful_checks"] == 1
    assert data[h]["total_checks"] == 1
    assert data[h]["last_latency_ms"] == 123
