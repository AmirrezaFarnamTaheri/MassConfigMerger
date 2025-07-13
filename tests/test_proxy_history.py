import asyncio
import json
from massconfigmerger.vpn_merger import UltimateVPNMerger, CONFIG


def test_proxy_history_update(tmp_path, monkeypatch):
    monkeypatch.setattr(CONFIG, "output_dir", str(tmp_path))
    merger = UltimateVPNMerger()
    h = merger.processor.create_semantic_hash("vmess://id@h:80")
    asyncio.run(merger._update_history(h, True, 0.123))
    asyncio.run(merger._save_proxy_history())
    data = json.loads((tmp_path / CONFIG.history_file).read_text())
    assert data[h]["successful_checks"] == 1
    assert data[h]["total_checks"] == 1
    assert data[h]["latency_ms"] == 123.0
