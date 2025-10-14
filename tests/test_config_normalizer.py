from __future__ import annotations

import base64
import json
from unittest.mock import patch

import pytest

from configstream.config import Settings
from configstream.core import config_normalizer


@pytest.mark.parametrize(
    "config, expected_host, expected_port",
    [
        # VLESS fallback case
        ("vless://uuid@test.com:443?encryption=none#test", "test.com", 443),
        # Invalid SSR
        ("ssr://INVALID_BASE64", None, None),
        # Oversized payload
        (f"vmess://{base64.b64encode(b'a' * 5000).decode()}", None, None),
        # Non-standard URI with regex fallback
        ("custom-proto://user@host.net:1234/path", "host.net", 1234),
    ],
)
def test_extract_host_port_edge_cases(config, expected_host, expected_port):
    """Test edge cases for extract_host_port."""
    host, port = config_normalizer.extract_host_port(
        config, max_decode_size=4096)
    assert host == expected_host
    assert port == expected_port


@pytest.mark.parametrize(
    "config, expected_normalized",
    [
        # Standard URL with params and fragment
        ("https://test.com/path?c=2&a=1#frag", "https://test.com/path?a=1&c=2"),
        # VLESS with JSON payload
        (
            f"vless://{base64.b64encode(json.dumps({'add': 'test.com', 'port': 443}).encode()).decode()}",
            f"vless://{base64.b64encode(json.dumps({'add': 'test.com', 'port': 443}, sort_keys=True).encode()).decode().rstrip('=')}",
        ),
        # Vmess with invalid JSON should not be modified
        ("vmess://INVALID_JSON?a=1", "vmess://INVALID_JSON?a=1"),
    ],
)
def test_normalize_url(config, expected_normalized):
    """Test the _normalize_url function."""
    assert config_normalizer._normalize_url(config) == expected_normalized


@pytest.mark.parametrize(
    "config1, config2, should_be_equal",
    [
        # Trojan with different fragments
        ("trojan://pass@host.com:443#frag1",
         "trojan://pass@host.com:443#frag2", True),
        # Trojan with different passwords
        ("trojan://pass1@host.com:443", "trojan://pass2@host.com:443", False),
        # SS with different fragments
        (
            f"ss://{base64.b64encode(b'aes-256-gcm:pass').decode()}@host.com:8080#frag1",
            f"ss://{base64.b64encode(b'aes-256-gcm:pass').decode()}@host.com:8080#frag2",
            True,
        ),
        # SS with different passwords
        (
            f"ss://{base64.b64encode(b'aes-256-gcm:pass1').decode()}@host.com:8080",
            f"ss://{base64.b64encode(b'aes-256-gcm:pass2').decode()}@host.com:8080",
            False,
        ),
        # Fallback to full URL hash
        ("unknown://config1", "unknown://config2", False),
    ],
)
def test_create_semantic_hash_protocols(config1, config2, should_be_equal):
    """Test semantic hashing for various protocols."""
    hash1 = config_normalizer.create_semantic_hash(config1, 0)
    hash2 = config_normalizer.create_semantic_hash(config2, 0)
    if should_be_equal:
        assert hash1 == hash2
    else:
        assert hash1 != hash2


@pytest.mark.parametrize(
    "config, expected_tuned",
    [
        # Should not be tuned
        ("vmess://some-data", "vmess://some-data"),
        ("not-a-uri", "not-a-uri"),
        # Should be tuned
        ("trojan://pass@host.com:443", "trojan://pass@host.com:443?mux=8&smux=4"),
        # Should overwrite existing
        ("trojan://pass@host.com:443?mux=1",
         "trojan://pass@host.com:443?mux=8&smux=4"),
    ],
)
def test_apply_tuning(config, expected_tuned):
    """Test the apply_tuning function."""
    settings = Settings()
    tuned = config_normalizer.apply_tuning(config, settings)
    assert tuned == expected_tuned


@pytest.mark.parametrize(
    "config",
    [
        "vless://test",  # Invalid base64
        "vmess://" + "a" * 5000,  # Oversized payload
        "ssr://invalid-base64",
        "ssr://" + "a" * 5000,
        "ssr://bm90aG9zdDpsb2NhbA==",  # Decodes to "nothost:local"
        "invalid-config",
    ],
)
def test_extract_host_port_failures(config: str):
    """Test extract_host_port with various invalid or problematic inputs."""
    host, port = config_normalizer.extract_host_port(config)
    assert host is None
    assert port is None


@pytest.mark.parametrize(
    "config",
    [
        "vless://test",  # Invalid base64
        # Incomplete JSON
        "vmess://" + base64.b64encode(b'{"add": "host"}').decode(),
        "vmess://" + "a" * 5000,
    ],
)
def test_normalize_url_failures(config: str):
    """Test that _normalize_url returns a partially normalized URL on error."""
    normalized = config_normalizer._normalize_url(config)
    # In case of error, it should still sort query params and remove fragment
    assert "#" not in normalized
    assert "a=1&b=2" in config_normalizer._normalize_url(config + "?b=2&a=1")


def test_apply_tuning_invalid_uri():
    """Test that apply_tuning returns the original config on ValueError."""
    config = "http://[::1"  # Malformed IPv6 URI
    settings = Settings()
    # This should trigger a ValueError and return the original config
    assert config_normalizer.apply_tuning(config, settings) == config


def test_extract_host_port_vless_fallback():
    """Test extract_host_port fallback for a VLESS URI that isn't base64."""
    config = "vless://uuid@example.com:443?encryption=none#test"
    host, port = config_normalizer.extract_host_port(config)
    assert host == "example.com"
    assert port == 443


def test_extract_host_port_ssr_not_enough_parts():
    """Test extract_host_port for SSR with not enough parts after decoding."""
    # This base64 decodes to "hostonly"
    config = "ssr://aG9zdG9ubHk="
    host, port = config_normalizer.extract_host_port(config)
    assert host is None
    assert port is None


def test_apply_tuning_no_double_slash():
    """Test apply_tuning with a config that has no double slash."""
    config = "trojan:password@example.com:443"
    tuned = config_normalizer.apply_tuning(config, Settings())
    assert tuned == config


@patch("configstream.core.config_normalizer.logging.debug")
def test_extract_host_port_vless_fallback_failure(mock_logging_debug):
    """Test that the vless host/port extraction fallback logs on failure."""
    # This config is invalid base64 and also not a valid URI with host/port
    config = "vless://!!!###"
    config_normalizer.extract_host_port(config)
    mock_logging_debug.assert_called_once_with(
        "extract_host_port vmess/vless fallback failed for: %s", config
    )


def test_extract_host_port_vmess_invalid_json():
    """Test host/port extraction with invalid vmess json to trigger fallback."""
    # This config has invalid base64, forcing the fallback parser.
    config = "vless://invalid-base64@1.2.3.4:443?encryption=none&type=ws#test"
    host, port = config_normalizer.extract_host_port(config)
    assert host == "1.2.3.4"
    assert port == 443


def test_extract_host_port_ssr_large_payload():
    """Test ssr:// config with a payload exceeding the max decode size."""
    # Create a dummy base64 string that is intentionally too long
    long_payload = "a" * 5000
    config = f"ssr://{long_payload}"
    host, port = config_normalizer.extract_host_port(config, max_decode_size=4096)
    assert host is None
    assert port is None


def test_normalize_url_vless_large_payload():
    """Test _normalize_url with a vless payload exceeding max decode size."""
    # A payload that is valid base64 but results in decoded data > max_decode_size
    large_json_payload = "eyJ2IjogIjIiLCAicHMiOiAidGVzdCIsICJhZGQiOiAiMS4yLjMuNCIsICJwb3J0IjogIjQ0MyIsICJpZCI6ICJ0ZXN0LWlkIn0="  # A valid payload
    long_config = f"vless://{large_json_payload * 50}"
    # We expect it to return the URL with sorted query but without decoding the large payload
    normalized = config_normalizer._normalize_url(long_config, max_decode_size=100)
    assert normalized.startswith("vless://")
    assert len(normalized) > len("vless://")


def test_get_parser_hysteria_schemes():
    """Test get_parser with all supported Hysteria schemes."""
    from configstream.core.parsers.hysteria import HysteriaParser
    config_hy2 = "hy2://password@1.2.3.4:443"
    config_hysteria2 = "hysteria2://password@1.2.3.4:443"

    parser_hy2 = config_normalizer.get_parser(config_hy2, 0)
    parser_hysteria2 = config_normalizer.get_parser(config_hysteria2, 0)

    assert isinstance(parser_hy2, HysteriaParser)
    assert isinstance(parser_hysteria2, HysteriaParser)


@patch("configstream.core.config_normalizer.urlparse")
def test_create_semantic_hash_exception_fallback(mock_urlparse):
    """Test the fallback mechanism in create_semantic_hash when urlparse fails."""
    mock_urlparse.side_effect = ValueError("mocked error")
    config = "invalid-config-string"
    idx = 42

    # The function should catch the exception and fall back to a simple hash
    h = config_normalizer.create_semantic_hash(config, idx)

    # We don't need to check the exact hash, just that it returns a 16-char string
    assert isinstance(h, str)
    assert len(h) == 16


def test_apply_tuning_no_scheme():
    """Test that apply_tuning does not modify a config string without a scheme."""
    config = "just-a-string"
    settings = Settings()
    assert config_normalizer.apply_tuning(config, settings) == config


def test_extract_host_port_vless_no_port():
    """Test vless config with hostname but no port to hit fallback log."""
    config = "vless://test-id@[::1]?encryption=none"
    host, port = config_normalizer.extract_host_port(config)
    # The outer function will return None, None because urlparse doesn't find a port
    assert host is None
    assert port is None


def test_extract_host_port_ssr_no_colon():
    config = "ssr://" + base64.urlsafe_b64encode(b"nohostorport").decode()
    host, port = config_normalizer.extract_host_port(config)
    assert host is None
    assert port is None


def test_extract_host_port_invalid_ipv6():
    config = "vless://[::1"
    host, port = config_normalizer.extract_host_port(config)
    assert host is None
    assert port is None


def test_normalize_url_invalid_payload():
    """Test _normalize_url with invalid base64 payload."""
    config = "vmess://invalid-base64-payload"
    # This should not raise an exception but return the url with no change to payload
    normalized = config_normalizer._normalize_url(config)
    assert normalized == "vmess://invalid-base64-payload"


def test_normalize_url_no_payload():
    config = "vmess://"
    normalized = config_normalizer._normalize_url(config)
    # urlunparse behavior: if netloc is empty, it doesn't produce "//"
    assert normalized == "vmess:"


def test_get_parser_unknown_scheme():
    parser = config_normalizer.get_parser("http://example.com", 0)
    assert parser is None

def test_extract_host_port_ssr_invalid_base64():
    """Test ssr config with invalid base64 to trigger logging."""
    config = "ssr://invalid-base64"
    host, port = config_normalizer.extract_host_port(config)
    assert host is None
    assert port is None

@patch("configstream.core.config_normalizer.urlunparse", side_effect=ValueError("mock error"))
def test_apply_tuning_unparse_error(mock_unparse):
    """Test apply_tuning when urlunparse raises an error."""
    config = "vless://test@1.2.3.4:443"
    settings = Settings()
    # The function should catch the error and return the original config
    result = config_normalizer.apply_tuning(config, settings)
    assert result == config
