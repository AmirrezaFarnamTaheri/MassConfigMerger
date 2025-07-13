import os
import sys
import json
import base64

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from clash_utils import config_to_clash_proxy


def test_vmess_parse_success():
    data = {
        "add": "host",
        "port": "443",
        "id": "uuid",
        "type": "auto",
        "ps": "name",
        "tls": "tls",
    }
    encoded = base64.b64encode(json.dumps(data).encode()).decode()
    link = f"vmess://{encoded}"
    proxy = config_to_clash_proxy(link, 0)
    assert proxy["type"] == "vmess"
    assert proxy["server"] == "host"
    assert proxy["port"] == 443
    assert proxy["tls"] is True


def test_vmess_parse_fallback():
    link = "vmess://uuid@host:443?aid=0&type=auto&security=tls#name"
    proxy = config_to_clash_proxy(link, 0)
    assert proxy["type"] == "vmess"
    assert proxy["server"] == "host"
    assert proxy["port"] == 443
    assert proxy["tls"] is True


def test_vmess_parse_options():
    data = {
        "add": "ex.com",
        "port": "443",
        "id": "uuid",
        "net": "ws",
        "path": "/ws",
        "host": "ex.com",
        "sni": "ex.com",
        "alpn": "h2",
        "flow": "xtls-rprx-origin",
        "tls": "tls",
    }
    link = "vmess://" + base64.b64encode(json.dumps(data).encode()).decode()
    proxy = config_to_clash_proxy(link, 0)
    assert proxy["network"] == "ws"
    assert proxy["path"] == "/ws"
    assert proxy["host"] == "ex.com"
    assert proxy["sni"] == "ex.com"
    assert proxy["alpn"] == "h2"
    assert proxy["flow"] == "xtls-rprx-origin"


def test_vmess_invalid_link():
    proxy = config_to_clash_proxy("vmess://invalid", 0)
    assert proxy["type"] == "vmess"
    assert proxy["server"] == "invalid"
