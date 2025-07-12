import os
import sys
import asyncio
import yaml
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from vpn_merger import UltimateVPNMerger, ConfigResult, CONFIG


def test_clash_proxies_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(CONFIG, "output_dir", str(tmp_path))
    monkeypatch.setattr(CONFIG, "write_clash_proxies", True)
    merger = UltimateVPNMerger()
    res1 = ConfigResult(
        config="vmess://uuid@host:80",
        protocol="VMess",
        host="host",
        port=80,
        ping_time=0.1,
        is_reachable=True,
        source_url="s",
    )
    res2 = ConfigResult(
        config="trojan://pw@host:443",
        protocol="Trojan",
        host="host",
        port=443,
        ping_time=0.2,
        is_reachable=True,
        source_url="s",
    )
    res3 = ConfigResult(
        config="naive://user:pass@host:8080",
        protocol="Naive",
        host="host",
        port=8080,
        ping_time=0.3,
        is_reachable=True,
        source_url="s",
    )
    res4 = ConfigResult(
        config="reality://uuid@host:443?flow=xtls-rprx-vision",
        protocol="Reality",
        host="host",
        port=443,
        ping_time=0.4,
        is_reachable=True,
        source_url="s",
    )
    res5 = ConfigResult(
        config="shadowtls://host:443",
        protocol="ShadowTLS",
        host="host",
        port=443,
        ping_time=0.5,
        is_reachable=True,
        source_url="s",
    )
    res6 = ConfigResult(
        config="brook://user@host:8080",
        protocol="Brook",
        host="host",
        port=8080,
        ping_time=0.6,
        is_reachable=True,
        source_url="s",
    )
    res7 = ConfigResult(
        config="juicity://pass@host:5555",
        protocol="Juicity",
        host="host",
        port=5555,
        ping_time=0.7,
        is_reachable=True,
        source_url="s",
    )
    results = [res1, res2, res3, res4, res5, res6, res7]
    stats = merger._analyze_results(results, [])
    asyncio.run(merger._generate_comprehensive_outputs(results, stats, 0.0))
    path = tmp_path / "vpn_clash_proxies.yaml"
    assert path.exists()
    data = yaml.safe_load(path.read_text())
    assert "proxies" in data
    assert len(data["proxies"]) == 7
    naive = next(p for p in data["proxies"] if p["type"] == "http")
    assert naive["username"] == "user"
    assert naive["password"] == "pass"
    assert naive["tls"] is True
    reality = next(p for p in data["proxies"] if p.get("flow"))
    assert reality["type"] == "vless"
    assert reality["tls"] is True
    assert any(p["type"] == "shadowtls" for p in data["proxies"])
    assert any(p["type"] == "brook" for p in data["proxies"])
    assert any(p["type"] == "juicity" for p in data["proxies"])
