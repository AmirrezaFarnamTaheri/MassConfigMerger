from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from configstream.core import (
    Proxy,
    generate_clash_config,
    process_and_test_proxies,
)

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

# --- Tests ---


class TestProxyParser:
    def test_parse_valid_vmess(self):
        proxy = Proxy.from_config(VALID_VMESS_CONFIG)
        assert proxy is not None
        assert proxy.protocol == "vmess"
        assert proxy.remarks == "My-VMess-Proxy"
        assert proxy.address == "server.example.com"
        assert proxy.port == 12345
        assert proxy.uuid == "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"

    def test_parse_valid_vless(self):
        proxy = Proxy.from_config(VALID_VLESS_CONFIG)
        assert proxy is not None
        assert proxy.protocol == "vless"
        assert proxy.remarks == "My-VLESS-Proxy"
        assert proxy.address == "server2.example.com"
        assert proxy.port == 54321
        assert proxy.uuid == "b1a2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"

    def test_parse_valid_ss(self):
        proxy = Proxy.from_config(VALID_SS_CONFIG)
        assert proxy is not None
        assert proxy.protocol == "shadowsocks"
        assert proxy.remarks == "My-SS-Proxy"
        assert proxy.address == "server3.example.com"
        assert proxy.port == 8888
        assert proxy._details["method"] == SS_METHOD
        assert proxy._details["password"] == SS_PASSWORD

    def test_parse_invalid_protocol(self):
        proxy = Proxy.from_config(INVALID_CONFIG)
        assert proxy is None

    def test_parse_malformed_vmess(self):
        proxy = Proxy.from_config(MALFORMED_VMESS_CONFIG)
        assert proxy is None

    def test_parse_valid_hy2(self):
        proxy = Proxy.from_config(VALID_HY2_CONFIG)
        assert proxy is not None
        assert proxy.protocol == "hysteria2"
        assert proxy.remarks == "My-Hysteria2-Proxy"
        assert proxy.address == "server4.example.com"
        assert proxy.port == 443
        assert proxy.uuid == "password"

    def test_parse_valid_tuic(self):
        proxy = Proxy.from_config(VALID_TUIC_CONFIG)
        assert proxy is not None
        assert proxy.protocol == "tuic"
        assert proxy.remarks == "My-TUIC-Proxy"
        assert proxy.address == "server5.example.com"
        assert proxy.port == 443
        assert proxy.uuid == "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"

    def test_parse_valid_wg(self):
        proxy = Proxy.from_config(VALID_WG_CONFIG)
        assert proxy is not None
        assert proxy.protocol == "wireguard"
        assert proxy.remarks == "My-WG-Proxy"
        assert proxy.address == "server6.example.com"
        assert proxy.port == 51820


class TestClashGenerator:
    def test_generate_clash_with_all_protocols(self):
        proxy1 = Proxy.from_config(VALID_VMESS_CONFIG)
        proxy1.is_working = True
        proxy2 = Proxy.from_config(VALID_VLESS_CONFIG)
        proxy2.is_working = True
        proxy3 = Proxy.from_config(VALID_SS_CONFIG)
        proxy3.is_working = True
        proxy4 = Proxy.from_config(VALID_TROJAN_CONFIG)
        proxy4.is_working = True
        proxies = [proxy1, proxy2, proxy3, proxy4]

        clash_yaml_str = generate_clash_config(proxies)
        clash_config = yaml.safe_load(clash_yaml_str)

        assert "proxies" in clash_config
        assert len(clash_config["proxies"]) == 4
        assert clash_config["proxies"][0]["type"] == "vmess"
        assert clash_config["proxies"][1]["type"] == "vless"
        assert clash_config["proxies"][2]["type"] == "ss"
        assert clash_config["proxies"][3]["type"] == "trojan"
        assert "proxy-groups" in clash_config
        assert "rules" in clash_config

    def test_generate_clash_with_no_working_proxies(self):
        proxy1 = Proxy.from_config(VALID_VMESS_CONFIG)
        proxy1.is_working = False
        proxies = [proxy1]

        clash_yaml_str = generate_clash_config(proxies)
        assert clash_yaml_str == ""


@pytest.mark.asyncio
async def test_process_and_test_proxies():
    """
    Tests the main proxy processing and testing pipeline.
    """
    # Create a mock for the progress bar
    mock_progress = MagicMock()

    # Mock the SingBoxWorker and its test_proxy method
    mock_worker = AsyncMock()
    mock_worker.test_proxy = AsyncMock()

    # Patch the Proxy.test method to use our mock worker
    with patch("configstream.core.Proxy.test", new_callable=AsyncMock) as mock_proxy_test:
        # Define the behavior of the mock
        async def side_effect(proxy, worker):
            if "vless" in proxy.config:
                proxy.is_working = True
                proxy.latency = 100
            else:
                proxy.is_working = False
            return proxy

        mock_proxy_test.side_effect = side_effect

        configs = [VALID_VMESS_CONFIG, VALID_VLESS_CONFIG]
        results = await process_and_test_proxies(configs, mock_progress)

        assert len(results) == 2

        working_proxies = [p for p in results if p.is_working]
        assert len(working_proxies) == 1
        assert working_proxies[0].protocol == "vless"
        assert working_proxies[0].latency == 100

        # Check that the progress bar was updated
        assert mock_progress.add_task.called
        assert mock_progress.update.call_count == 2
