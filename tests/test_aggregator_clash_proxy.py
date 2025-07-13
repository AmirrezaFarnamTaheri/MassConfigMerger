import yaml

from massconfigmerger import aggregator_tool
from massconfigmerger.config import Settings


def test_aggregator_clash_proxy(tmp_path):
    cfg = Settings(output_dir=str(tmp_path), write_clash=True)
    import base64, json

    vmess_data = {
        "add": "v.example",
        "port": "443",
        "id": "uuid",
        "net": "ws",
        "host": "host",
        "path": "/ws",
        "tls": "tls",
    }
    vmess_link = "vmess://" + base64.b64encode(json.dumps(vmess_data).encode()).decode()

    vless_link = (
        "vless://uuid@vl.example:443?type=grpc&serviceName=s&security=tls"
        "&sni=example.com&fp=chrome#vl"
    )

    raw_ssr = (
        "example.com:443:origin:aes-128-gcm:plain:cGFzcw==/?remarks=bmFtZQ=="
        "&obfsparam=c2FsdA==&protoparam=YXV0aA=="
    )
    ssr_link = "ssr://" + base64.urlsafe_b64encode(raw_ssr.encode()).decode().strip("=")

    configs = [
        vmess_link,
        vless_link,
        ssr_link,
        (
            "reality://uuid@host:443?flow=xtls-rprx-vision&publicKey=pub"
            "&short-id=123&sni=site.com&fp=chrome"
        ),
        "naive://user:pass@host:443",
    ]
    aggregator_tool.output_files(configs, tmp_path, cfg)
    data = yaml.safe_load((tmp_path / "clash.yaml").read_text())
    reality = next(p for p in data["proxies"] if p.get("flow") == "xtls-rprx-vision")
    assert reality["type"] == "vless"
    assert reality["tls"] is True
    assert reality["sni"] == "site.com"
    assert reality["fp"] == "chrome"
    assert reality["reality-opts"]["public-key"] == "pub"
    assert reality["reality-opts"]["short-id"] == "123"

    vmess = next(p for p in data["proxies"] if p["type"] == "vmess")
    assert vmess["network"] == "ws"
    assert vmess["host"] == "host"
    assert vmess["path"] == "/ws"
    assert vmess["tls"] is True

    vless = next(p for p in data["proxies"] if p.get("network") == "grpc")
    assert vless["type"] == "vless"
    assert vless["tls"] is True
    assert vless["fp"] == "chrome"

    ssr = next(p for p in data["proxies"] if p["type"] == "ssr")
    assert ssr["protocol"] == "origin"
    assert ssr["obfs"] == "plain"
    assert ssr["password"] == "pass"

    naive = next(p for p in data["proxies"] if p["type"] == "http")
    assert naive["tls"] is True
