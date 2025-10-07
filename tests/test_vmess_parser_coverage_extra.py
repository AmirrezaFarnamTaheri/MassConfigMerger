import pytest
from configstream.core.parsers.vmess import VmessParser
import base64
import json

def test_vmess_parser_ws_headers():
    """Test parsing of ws-headers in the primary vmess parser."""
    vmess_data = {
        "ps": "vmess-ws-headers",
        "add": "example.com",
        "port": 80,
        "id": "uuid",
        "net": "ws",
        "ws-headers": {"Host": "example.com"},
    }
    encoded_data = base64.b64encode(json.dumps(vmess_data).encode()).decode()
    config = f"vmess://{encoded_data}"
    parser = VmessParser(config, 0)
    result = parser.parse()
    assert result["ws-headers"]["Host"] == "example.com"

def test_vmess_parser_fallback_security():
    """Test the fallback vmess parser with the 'security' parameter."""
    config = "vmess://uuid@example.com:443?security=tls"
    parser = VmessParser(config, 0)
    result = parser.parse()
    assert result["tls"] is True

def test_vmess_parser_fallback_mode():
    """Test the fallback vmess parser with the 'mode' parameter."""
    config = "vmess://uuid@example.com:80?mode=ws"
    parser = VmessParser(config, 0)
    result = parser.parse()
    assert result["network"] == "ws"

def test_vmess_parser_fallback_other_keys():
    """Test the fallback vmess parser with other query parameters."""
    config = "vmess://uuid@example.com:80?host=h&path=p&sni=s&alpn=a&fp=f&flow=fl&serviceName=sn"
    parser = VmessParser(config, 0)
    result = parser.parse()
    assert result["host"] == "h"
    assert result["path"] == "p"
    assert result["sni"] == "s"
    assert result["alpn"] == "a"
    assert result["fp"] == "f"
    assert result["flow"] == "fl"
    assert result["serviceName"] == "sn"


def test_vmess_parser_ws_opts():
    """Test parsing of ws-opts in the primary vmess parser."""
    vmess_data = {
        "ps": "vmess-ws-opts",
        "add": "example.com",
        "port": 80,
        "id": "uuid",
        "net": "ws",
        "ws-opts": {"headers": {"Host": "example.com"}},
    }
    encoded_data = base64.b64encode(json.dumps(vmess_data).encode()).decode()
    config = f"vmess://{encoded_data}"
    parser = VmessParser(config, 0)
    result = parser.parse()
    assert result["ws-headers"]["Host"] == "example.com"