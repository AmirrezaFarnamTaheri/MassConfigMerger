from __future__ import annotations

import base64
import json

from configstream.parsers import parse_config

# --- Test Data ---

# VMess
VALID_VMESS_DETAILS = {
    "v": "2",
    "ps": "My-VMess-Proxy",
    "add": "server.example.com",
    "port": "12345",
    "id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
    "aid": "0",
    "net": "ws",
    "type": "none",
    "host": "server.example.com",
    "path": "/",
    "tls": "tls",
    "scy": "auto",
}
VALID_VMESS_JSON = json.dumps(VALID_VMESS_DETAILS)
VALID_VMESS_BASE64 = base64.b64encode(VALID_VMESS_JSON.encode("utf-8")).decode("utf-8")
VALID_VMESS_CONFIG = f"vmess://{VALID_VMESS_BASE64}"

# VLESS
VALID_VLESS_CONFIG = "vless://b1a2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6@server2.example.com:54321?type=ws&security=tls#My-VLESS-Proxy"

# Shadowsocks (SS)
SS_METHOD = "aes-256-gcm"
SS_PASSWORD = "a-very-secret-password"
SS_USER_INFO = base64.b64encode(f"{SS_METHOD}:{SS_PASSWORD}".encode("utf-8")).decode("utf-8")
VALID_SS_CONFIG = f"ss://{SS_USER_INFO}@server3.example.com:8888#My-SS-Proxy"

# Hysteria2
VALID_HY2_CONFIG = "hy2://password@server4.example.com:443?insecure=1#My-Hysteria2-Proxy"

# TUIC
VALID_TUIC_CONFIG = "tuic://a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6:password@server5.example.com:443?congestion_control=bbr#My-TUIC-Proxy"

# WireGuard
VALID_WG_CONFIG = "wg://server6.example.com:51820?private_key=...&public_key=...#My-WG-Proxy"

# Trojan
VALID_TROJAN_CONFIG = "trojan://password@server7.example.com:443#My-Trojan-Proxy"


INVALID_CONFIG = "invalid-protocol://some-data"
MALFORMED_VMESS_CONFIG = "vmess://this-is-not-base64"


def test_parse_valid_vmess():
    proxy = parse_config(VALID_VMESS_CONFIG)
    assert proxy is not None
    assert proxy.protocol == "vmess"
    assert proxy.remarks == "My-VMess-Proxy"
    assert proxy.address == "server.example.com"
    assert proxy.port == 12345
    assert proxy.uuid == "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"


def test_parse_valid_vless():
    proxy = parse_config(VALID_VLESS_CONFIG)
    assert proxy is not None
    assert proxy.protocol == "vless"
    assert proxy.remarks == "My-VLESS-Proxy"
    assert proxy.address == "server2.example.com"
    assert proxy.port == 54321
    assert proxy.uuid == "b1a2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"


def test_parse_valid_ss():
    proxy = parse_config(VALID_SS_CONFIG)
    assert proxy is not None
    assert proxy.protocol == "shadowsocks"
    assert proxy.remarks == "My-SS-Proxy"
    assert proxy.address == "server3.example.com"
    assert proxy.port == 8888
    assert proxy._details["method"] == SS_METHOD
    assert proxy._details["password"] == SS_PASSWORD


def test_parse_invalid_protocol():
    proxy = parse_config(INVALID_CONFIG)
    assert proxy is None


def test_parse_malformed_vmess():
    proxy = parse_config(MALFORMED_VMESS_CONFIG)
    assert proxy is None


def test_parse_valid_hy2():
    proxy = parse_config(VALID_HY2_CONFIG)
    assert proxy is not None
    assert proxy.protocol == "hysteria2"
    assert proxy.remarks == "My-Hysteria2-Proxy"
    assert proxy.address == "server4.example.com"
    assert proxy.port == 443
    assert proxy.uuid == "password"


def test_parse_valid_tuic():
    proxy = parse_config(VALID_TUIC_CONFIG)
    assert proxy is not None
    assert proxy.protocol == "tuic"
    assert proxy.remarks == "My-TUIC-Proxy"
    assert proxy.address == "server5.example.com"
    assert proxy.port == 443
    assert proxy.uuid == "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"


def test_parse_valid_wg():
    proxy = parse_config(VALID_WG_CONFIG)
    assert proxy is not None
    assert proxy.protocol == "wireguard"
    assert proxy.remarks == "My-WG-Proxy"
    assert proxy.address == "server6.example.com"
    assert proxy.port == 51820


def test_parse_valid_trojan():
    proxy = parse_config(VALID_TROJAN_CONFIG)
    assert proxy is not None
    assert proxy.protocol == "trojan"
    assert proxy.remarks == "My-Trojan-Proxy"
    assert proxy.address == "server7.example.com"
    assert proxy.port == 443


def test_parse_valid_hysteria():
    proxy = parse_config("hysteria://example.com:443?protocol=udp&auth=password#Hysteria%20Test")
    assert proxy is not None
    assert proxy.protocol == "hysteria"
    assert proxy.address == "example.com"
    assert proxy.port == 443
    assert proxy.remarks == "Hysteria Test"
    assert proxy._details["protocol"] == "udp"
    assert proxy._details["auth"] == "password"


def test_parse_valid_generic_http():
    proxy = parse_config("http://user:pass@example.com:8080#HTTP%20Test")
    assert proxy is not None
    assert proxy.protocol == "http"
    assert proxy.address == "example.com"
    assert proxy.port == 8080
    assert proxy.uuid == "user"
    assert proxy._details["password"] == "pass"
    assert proxy.remarks == "HTTP Test"


def test_parse_valid_naive():
    proxy = parse_config("naive+https://user:pass@example.com:443#Naive%20Test")
    assert proxy is not None
    assert proxy.protocol == "naive"
    assert proxy.address == "example.com"
    assert proxy.port == 443
    assert proxy.uuid == "user"
    assert proxy._details["password"] == "pass"
    assert proxy.remarks == "Naive Test"


def test_parse_ss_no_user_info():
    proxy = parse_config("ss://example.com:8388#Invalid")
    assert proxy is None


def test_parse_ss_invalid_base64():
    proxy = parse_config("ss://invalid-base64@example.com:8388#Invalid")
    assert proxy is None
