import pytest
import base64
from configstream.core.parsers.shadowsocks import ShadowsocksParser
from configstream.exceptions import ParserError


def test_ss_parser_with_plugin():
    """Test SS parser with a plugin parameter."""
    user_info = base64.urlsafe_b64encode(b"aes-256-gcm:test").decode().rstrip("=")
    uri = f"ss://{user_info}@1.2.3.4:1234?plugin=obfs-local;obfs=http#test"
    parser = ShadowsocksParser(uri, 0)
    result = parser.parse()
    assert result is not None
    assert result["plugin"] == "obfs-local"
    assert result["plugin-opts"] == "obfs=http"


def test_ss_parser_with_empty_plugin():
    """Test SS parser with an empty plugin parameter."""
    user_info = base64.urlsafe_b64encode(b"aes-256-gcm:test").decode().rstrip("=")
    uri = f"ss://{user_info}@1.2.3.4:1234?plugin=#test_empty_plugin"
    parser = ShadowsocksParser(uri, 1)
    result = parser.parse()
    assert result is not None
    assert "plugin" not in result


def test_ss_parser_udp_and_tfo():
    """Test SS parser with udp and tfo flags."""
    user_info = base64.urlsafe_b64encode(b"aes-256-gcm:test").decode().rstrip("=")
    uri = f"ss://{user_info}@1.2.3.4:1234?udp=true&tfo=true#test_udp_tfo"
    parser = ShadowsocksParser(uri, 2)
    result = parser.parse()
    assert result is not None
    assert result["udp"] is True
    assert result["tfo"] is True


def test_ss_parser_invalid_base64_userinfo():
    """Test SS parser with invalid base64 in the userinfo part."""
    uri = "ss://invalid-base64@1.2.3.4:1234"
    parser = ShadowsocksParser(uri, 3)
    with pytest.raises(ParserError):
        parser.parse()