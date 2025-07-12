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
