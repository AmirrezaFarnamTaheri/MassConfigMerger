import asyncio
import yaml
from pathlib import Path

from massconfigmerger.vpn_merger import UltimateVPNMerger, ConfigResult, CONFIG


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
        config="reality://uuid@host:443?flow=xtls-rprx-vision&pbk=pub&sid=123",
        protocol="Reality",
        host="host",
        port=443,
        ping_time=0.4,
        is_reachable=True,
        source_url="s",
    )
    res5 = ConfigResult(
        config=(
            "tuic://uuid:pw@host:10443?alpn=h3&congestion-control=bbr"
            "&udp-relay-mode=native"
        ),
        protocol="TUIC",
        host="host",
        port=10443,
        ping_time=0.5,
        is_reachable=True,
        source_url="s",
    )
    res6 = ConfigResult(
        config=(
            "hy2://pass@host:8443?peer=example.com&insecure=1&obfs=obfs"
            "&obfs-password=secret"
        ),
        protocol="Hysteria2",
        host="host",
        port=8443,
        ping_time=0.6,
        is_reachable=True,
        source_url="s",
    )
    results = [res1, res2, res3, res4, res5, res6]
    stats = merger._analyze_results(results, [])
    asyncio.run(merger._generate_comprehensive_outputs(results, stats, 0.0))
    path = tmp_path / "vpn_clash_proxies.yaml"
    assert path.exists()
    data = yaml.safe_load(path.read_text())
    assert "proxies" in data
    assert len(data["proxies"]) == 6
    naive = next(p for p in data["proxies"] if p["type"] == "http")
    assert naive["username"] == "user"
    assert naive["password"] == "pass"
    assert naive["tls"] is True
    reality = next(p for p in data["proxies"] if p.get("flow"))
    assert reality["type"] == "vless"
    assert reality["tls"] is True
    assert reality["reality-opts"]["public-key"] == "pub"
    assert reality["reality-opts"]["short-id"] == "123"

    tuic = next(p for p in data["proxies"] if p["type"] == "tuic")
    assert tuic["uuid"] == "uuid"
    assert tuic["password"] == "pw"
    assert tuic["alpn"] == "h3"
    assert tuic["congestion-control"] == "bbr"
    assert tuic["udp-relay-mode"] == "native"

    hy2 = next(p for p in data["proxies"] if p["type"] == "hysteria2")
    assert hy2["password"] == "pass"
    assert hy2["peer"] == "example.com"
    assert hy2["insecure"] == "1"
    assert hy2["obfs"] == "obfs"
    assert hy2["obfs_password"] == "secret"

    singbox = tmp_path / "vpn_singbox.json"
    assert singbox.exists()
    import json
    sdata = json.loads(singbox.read_text())
    types = [ob["type"] for ob in sdata.get("outbounds", [])]
    assert "tuic" in types and "hysteria2" in types
