from __future__ import annotations

import base64
import pytest
from unittest.mock import patch
from massconfigmerger.config import Settings
from massconfigmerger.core.config_normalizer import (
    extract_host_port,
    _normalize_url,
    create_semantic_hash,
    apply_tuning,
)


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
    host, port = extract_host_port(config)
    assert host is None
    assert port is None


@pytest.mark.parametrize(
    "config",
    [
        "vless://test",  # Invalid base64
        "vmess://" + base64.b64encode(b'{"add": "host"}').decode(),  # Incomplete JSON
        "vmess://" + "a" * 5000,
    ],
)
def test_normalize_url_failures(config: str):
    """Test that _normalize_url returns a partially normalized URL on error."""
    normalized = _normalize_url(config)
    # In case of error, it should still sort query params and remove fragment
    assert "#" not in normalized
    assert "a=1&b=2" in _normalize_url(config + "?b=2&a=1")


@pytest.mark.parametrize(
    "config",
    [
        "vless://test",  # Invalid base64
        "vmess://" + "a" * 5000,
        "ss://invalid-base64@host:port",
        "ss://" + "a" * 5000,
        "trojan://user:pass@host:port?sni=invalid-sni-that-causes-error", # hypothetical error case
    ],
)
def test_create_semantic_hash_failures(config: str):
    """Test that create_semantic_hash still produces a hash on parsing failures."""
    # The function should not raise an exception and should return a valid hash.
    # The exact hash value is not important, only that one is generated.
    assert isinstance(create_semantic_hash(config), str)
    assert len(create_semantic_hash(config)) == 16


def test_create_semantic_hash_no_host_port():
    """Test create_semantic_hash when host and port cannot be extracted."""
    config = "vless://some-id@?type=ws"
    # When host/port can't be found, it should hash the normalized config string
    assert create_semantic_hash(config) is not None


def test_apply_tuning_invalid_uri():
    """Test that apply_tuning returns the original config on ValueError."""
    config = "http://[::1"  # Malformed IPv6 URI
    settings = Settings()
    # This should trigger a ValueError and return the original config
    assert apply_tuning(config, settings) == config




def test_create_semantic_hash_trojan_no_user_pass():
    """Test create_semantic_hash for a trojan link with no user/pass."""
    config = "trojan://example.com:443"
    h1 = create_semantic_hash(config)
    h2 = create_semantic_hash("trojan://password@example.com:443")
    assert h1 is not None
    assert h1 != h2