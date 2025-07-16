import asyncio
import json
import sys
from pathlib import Path

from massconfigmerger.vpn_merger import UltimateVPNMerger
from massconfigmerger import vpn_merger
from massconfigmerger.config import Settings
from massconfigmerger.result_processor import CONFIG


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


def test_cli_history_file(monkeypatch, tmp_path):
    recorded = {}

    def fake_detect_and_run(path=None):
        merger = UltimateVPNMerger()
        recorded["path"] = merger.history_path
        h = merger.processor.create_semantic_hash("vmess://id@h:80")
        asyncio.run(merger._update_history(h, True, 0.1))
        asyncio.run(merger._save_proxy_history())
        return None

    monkeypatch.setattr(vpn_merger, "detect_and_run", fake_detect_and_run)
    monkeypatch.setattr(vpn_merger, "load_config", lambda: Settings(output_dir=str(tmp_path)))
    monkeypatch.setattr(sys, "argv", [
        "vpn_merger.py",
        "--output-dir",
        str(tmp_path),
        "--history-file",
        "custom.json",
    ])

    vpn_merger.main()

    assert recorded["path"] == tmp_path / "custom.json"
    assert (tmp_path / "custom.json").exists()
