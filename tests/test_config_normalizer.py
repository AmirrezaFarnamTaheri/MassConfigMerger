from __future__ import annotations

import base64
import json

import pytest

from massconfigmerger.config import Settings
from massconfigmerger.core import config_normalizer


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
    host, port = config_normalizer.extract_host_port(config, max_decode_size=4096)
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
        (f"vmess://INVALID_JSON?a=1", "vmess://INVALID_JSON?a=1"),
    ],
)
def test_normalize_url(config, expected_normalized):
    """Test the _normalize_url function."""
    assert config_normalizer._normalize_url(config) == expected_normalized


@pytest.mark.parametrize(
    "config1, config2, should_be_equal",
    [
        # Trojan with different fragments
        ("trojan://pass@host.com:443#frag1", "trojan://pass@host.com:443#frag2", True),
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
    hash1 = config_normalizer.create_semantic_hash(config1)
    hash2 = config_normalizer.create_semantic_hash(config2)
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
        ("trojan://pass@host.com:443?mux=1", "trojan://pass@host.com:443?mux=8&smux=4"),
    ],
)
def test_apply_tuning(config, expected_tuned):
    """Test the apply_tuning function."""
    settings = Settings()
    tuned = config_normalizer.apply_tuning(config, settings)
    assert tuned == expected_tuned