import asyncio
import base64
import csv
import json
import os
import sys
import yaml

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from vpn_merger import UltimateVPNMerger, ConfigResult, CONFIG


def test_generate_comprehensive_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(CONFIG, "output_dir", str(tmp_path))
    monkeypatch.setattr(CONFIG, "write_clash_proxies", True)
    merger = UltimateVPNMerger()

    result = ConfigResult(
        config="vmess://uuid@host:80",
        protocol="VMess",
        host="host",
        port=80,
        ping_time=0.1,
        is_reachable=True,
        source_url="s",
    )
    stats = merger._analyze_results([result], [])
    asyncio.run(merger._generate_comprehensive_outputs([result], stats, 0.0))

    raw = tmp_path / "vpn_subscription_raw.txt"
    b64 = tmp_path / "vpn_subscription_base64.txt"
    csv_file = tmp_path / "vpn_detailed.csv"
    json_report = tmp_path / "vpn_report.json"
    singbox = tmp_path / "vpn_singbox.json"
    clash = tmp_path / "clash.yaml"
    proxies = tmp_path / "vpn_clash_proxies.yaml"

    for p in [raw, b64, csv_file, json_report, singbox, clash, proxies]:
        assert p.exists()

    assert base64.b64decode(b64.read_text()).decode() == raw.read_text()

    with csv_file.open() as f:
        rows = list(csv.reader(f))
    assert rows[0][0] == "Config"
    assert len(rows) == 2

    data = json.loads(json_report.read_text())
    assert data["output_files"]["json_report"] == str(json_report)

    assert "outbounds" in json.loads(singbox.read_text())
    assert "proxies" in yaml.safe_load(clash.read_text())
    assert "proxies" in yaml.safe_load(proxies.read_text())
