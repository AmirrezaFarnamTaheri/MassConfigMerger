import os
import json
import asyncio
from pathlib import Path

from massconfigmerger.vpn_merger import UltimateVPNMerger, ConfigResult, CONFIG


def test_json_report_prefix(monkeypatch, tmp_path):
    monkeypatch.setattr(CONFIG, "output_dir", str(tmp_path))
    merger = UltimateVPNMerger()
    res = ConfigResult(
        config="vmess://dXNlcjpwYXNzd0BleGFtcGxlLmNvbQ==",
        protocol="VMess",
        host="example.com",
        port=443,
        ping_time=0.1,
        is_reachable=True,
        source_url="src",
    )
    stats = merger._analyze_results([res], [])
    asyncio.run(
        merger._generate_comprehensive_outputs([res], stats, 0.0, prefix="batch1_")
    )
    report_file = tmp_path / "batch1_vpn_report.json"
    with report_file.open() as f:
        data = json.load(f)
    assert data["output_files"]["json_report"] == str(report_file)
