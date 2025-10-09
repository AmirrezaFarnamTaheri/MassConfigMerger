import pytest
import base64
from unittest.mock import patch
from configstream.core.config_normalizer import (
    extract_host_port,
    _normalize_url,
    get_parser,
    create_semantic_hash,
    apply_tuning,
)
from configstream.config import Settings
from configstream.core.parsers.hysteria import HysteriaParser


def test_extract_host_port_vmess_invalid_json():
    """Test host/port extraction with invalid vmess json to trigger fallback."""
    # This config has invalid base64, forcing the fallback parser.
    config = "vless://invalid-base64@1.2.3.4:443?encryption=none&type=ws#test"
    host, port = extract_host_port(config)
    assert host == "1.2.3.4"
    assert port == 443


def test_extract_host_port_ssr_large_payload():
    """Test ssr:// config with a payload exceeding the max decode size."""
    # Create a dummy base64 string that is intentionally too long
    long_payload = "a" * 5000
    config = f"ssr://{long_payload}"
    host, port = extract_host_port(config, max_decode_size=4096)
    assert host is None
    assert port is None


def test_normalize_url_vless_large_payload():
    """Test _normalize_url with a vless payload exceeding max decode size."""
    # A payload that is valid base64 but results in decoded data > max_decode_size
    large_json_payload = "eyJ2IjogIjIiLCAicHMiOiAidGVzdCIsICJhZGQiOiAiMS4yLjMuNCIsICJwb3J0IjogIjQ0MyIsICJpZCI6ICJ0ZXN0LWlkIn0="  # A valid payload
    long_config = f"vless://{large_json_payload * 50}"
    # We expect it to return the URL with sorted query but without decoding the large payload
    normalized = _normalize_url(long_config, max_decode_size=100)
    assert normalized.startswith("vless://")
    assert len(normalized) > len("vless://")


def test_get_parser_hysteria_schemes():
    """Test get_parser with all supported Hysteria schemes."""
    config_hy2 = "hy2://password@1.2.3.4:443"
    config_hysteria2 = "hysteria2://password@1.2.3.4:443"

    parser_hy2 = get_parser(config_hy2, 0)
    parser_hysteria2 = get_parser(config_hysteria2, 0)

    assert isinstance(parser_hy2, HysteriaParser)
    assert isinstance(parser_hysteria2, HysteriaParser)


@patch("configstream.core.config_normalizer.urlparse")
def test_create_semantic_hash_exception_fallback(mock_urlparse):
    """Test the fallback mechanism in create_semantic_hash when urlparse fails."""
    mock_urlparse.side_effect = ValueError("mocked error")
    config = "invalid-config-string"
    idx = 42

    # The function should catch the exception and fall back to a simple hash
    h = create_semantic_hash(config, idx)

    # We don't need to check the exact hash, just that it returns a 16-char string
    assert isinstance(h, str)
    assert len(h) == 16


def test_apply_tuning_no_scheme():
    """Test that apply_tuning does not modify a config string without a scheme."""
    config = "just-a-string"
    settings = Settings()
    assert apply_tuning(config, settings) == config


def test_extract_host_port_vless_no_port():
    """Test vless config with hostname but no port to hit fallback log."""
    config = "vless://test-id@[::1]?encryption=none"
    host, port = extract_host_port(config)
    # The outer function will return None, None because urlparse doesn't find a port
    assert host is None
    assert port is None


def test_extract_host_port_ssr_no_colon():
    config = "ssr://" + base64.urlsafe_b64encode(b"nohostorport").decode()
    host, port = extract_host_port(config)
    assert host is None
    assert port is None


def test_extract_host_port_invalid_ipv6():
    config = "vless://[::1"
    host, port = extract_host_port(config)
    assert host is None
    assert port is None


def test_normalize_url_invalid_payload():
    """Test _normalize_url with invalid base64 payload."""
    config = "vmess://invalid-base64-payload"
    # This should not raise an exception but return the url with no change to payload
    normalized = _normalize_url(config)
    assert normalized == "vmess://invalid-base64-payload"


def test_normalize_url_no_payload():
    config = "vmess://"
    normalized = _normalize_url(config)
    # urlunparse behavior: if netloc is empty, it doesn't produce "//"
    assert normalized == "vmess:"


def test_get_parser_unknown_scheme():
    parser = get_parser("http://example.com", 0)
    assert parser is None

def test_extract_host_port_ssr_invalid_base64():
    """Test ssr config with invalid base64 to trigger logging."""
    config = "ssr://invalid-base64"
    host, port = extract_host_port(config)
    assert host is None
    assert port is None

@patch("configstream.core.config_normalizer.urlunparse", side_effect=ValueError("mock error"))
def test_apply_tuning_unparse_error(mock_unparse):
    """Test apply_tuning when urlunparse raises an error."""
    config = "vless://test@1.2.3.4:443"
    settings = Settings()
    # The function should catch the error and return the original config
    result = apply_tuning(config, settings)
    assert result == config