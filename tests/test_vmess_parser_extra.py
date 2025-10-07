from __future__ import annotations

import base64
import json

from configstream.core.parsers.vmess import VmessParser


def test_parse_vmess_with_security_key():
    """Test parsing a VMess config with the 'security' key instead of 'tls'."""
    vmess_data = {
        "ps": "vmess-security",
        "add": "example.com",
        "port": 443,
        "id": "uuid",
        "aid": 0,
        "type": "none",
        "net": "ws",
        "security": "tls",  # Use the 'security' key
    }
    encoded_data = base64.b64encode(json.dumps(vmess_data).encode()).decode()
    config = f"vmess://{encoded_data}"

    parser = VmessParser(config, 0)
    result = parser.parse()

    assert result is not None
    assert result["tls"] is True


def test_parse_vmess_with_ws_opts():
    """Test parsing a VMess config with headers in 'ws-opts'."""
    vmess_data = {
        "ps": "vmess-ws-opts",
        "add": "example.com",
        "port": 80,
        "id": "uuid",
        "net": "ws",
        "ws-opts": {
            "path": "/path",
            "headers": {
                "Host": "example.com"
            }
        }
    }
    encoded_data = base64.b64encode(json.dumps(vmess_data).encode()).decode()
    config = f"vmess://{encoded_data}"

    parser = VmessParser(config, 0)
    result = parser.parse()

    assert result is not None
    assert result.get("ws-headers") is not None
    assert result["ws-headers"]["Host"] == "example.com"


def test_parse_vmess_fallback_with_security():
    """Test the fallback vmess parser with the 'security' query parameter."""
    config = "vmess://uuid@example.com:443?security=tls#FallbackSecurity"
    parser = VmessParser(config, 0)
    result = parser.parse()

    assert result is not None
    assert result["tls"] is True


def test_parse_vmess_fallback_with_mode():
    """Test the fallback vmess parser with the 'mode' query parameter."""
    config = "vmess://uuid@example.com:80?mode=ws#FallbackMode"
    parser = VmessParser(config, 0)
    result = parser.parse()

    assert result is not None
    assert result["network"] == "ws"