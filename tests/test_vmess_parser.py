import pytest
from configstream.core.parsers.vmess import VmessParser
from configstream.exceptions import ParserError
import base64
import json


def test_vmess_parser_fallback_no_username():
    """Test the fallback vmess parser when there is no username."""
    config = "vmess://@example.com:443"
    parser = VmessParser(config, 0)
    result = parser.parse()
    assert result["uuid"] == ""


def test_vmess_parser_get_identifier_no_id():
    """Test get_identifier when the JSON has no 'id' or 'uuid'."""
    vmess_data = {"add": "example.com", "port": 443}
    encoded_data = base64.b64encode(json.dumps(vmess_data).encode()).decode()
    config = f"vmess://{encoded_data}"
    parser = VmessParser(config, 0)
    assert parser.get_identifier() is None


def test_vmess_parser_get_identifier_fallback_no_username():
    """Test get_identifier fallback when there is no username."""
    config = "vmess://:443"
    parser = VmessParser(config, 0)
    assert parser.get_identifier() == ""


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