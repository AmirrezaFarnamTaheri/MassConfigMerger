import asyncio
import base64
import csv
import json
import yaml

from massconfigmerger.vpn_merger import UltimateVPNMerger
from massconfigmerger.result_processor import ConfigResult, CONFIG


def test_generate_comprehensive_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(CONFIG, "output_dir", str(tmp_path))
    monkeypatch.setattr(CONFIG, "write_clash_proxies", True)
    monkeypatch.setattr(CONFIG, "xyz_file", "xyz.conf")
    merger = UltimateVPNMerger()

    result = ConfigResult(
        config="vmess://uuid@host:80",
        protocol="VMess",
        host="host",
        port=80,
        ping_time=0.1,
        is_reachable=True,
        source_url="https://src.example",
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
    xyz = tmp_path / "xyz.conf"

    for p in [raw, b64, csv_file, json_report, singbox, clash, proxies, xyz]:
        assert p.exists()

    assert base64.b64decode(b64.read_text()).decode() == raw.read_text()

    with csv_file.open() as f:
        rows = list(csv.reader(f))
    assert rows[0] == [
        "config",
        "protocol",
        "host",
        "port",
        "ping_ms",
        "reachable",
        "source_url",
        "country",
    ]
    assert len(rows) == 2

    data = json.loads(json_report.read_text())
    assert data["output_files"]["json_report"] == str(json_report)

    assert "outbounds" in json.loads(singbox.read_text())
    clash_data = yaml.safe_load(clash.read_text())
    assert "proxies" in clash_data
    groups = clash_data.get("proxy-groups", [])
    assert any(g.get("name") == "⚡ Auto-Select" and g.get("type") == "url-test" for g in groups)
    manual = next(g for g in groups if g.get("name") == "🔰 MANUAL")
    assert manual["proxies"][0] == "⚡ Auto-Select"
    assert clash_data.get("rules") == ["MATCH,🔰 MANUAL"]
    proxy_name = clash_data["proxies"][0]["name"]
    assert proxy_name == "🏳 ?? - src.example - 100ms"
    assert "proxies" in yaml.safe_load(proxies.read_text())
    from massconfigmerger.advanced_converters import generate_xyz_conf
    expected_xyz = generate_xyz_conf([
        {
            "name": "vmess-0",
            "type": "vmess",
            "server": "host",
            "port": 80,
        }
    ])
    assert xyz.read_text() == expected_xyz
