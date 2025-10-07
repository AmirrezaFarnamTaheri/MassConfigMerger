from __future__ import annotations

import base64
import pytest
from unittest.mock import patch
from configstream.config import Settings
from configstream.core.config_normalizer import (
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
    assert isinstance(create_semantic_hash(config, 0), str)
    assert len(create_semantic_hash(config, 0)) == 16


def test_create_semantic_hash_no_host_port():
    """Test create_semantic_hash when host and port cannot be extracted."""
    config = "vless://some-id@?type=ws"
    # When host/port can't be found, it should hash the normalized config string
    assert create_semantic_hash(config, 0) is not None


def test_apply_tuning_invalid_uri():
    """Test that apply_tuning returns the original config on ValueError."""
    config = "http://[::1"  # Malformed IPv6 URI
    settings = Settings()
    # This should trigger a ValueError and return the original config
    assert apply_tuning(config, settings) == config




def test_create_semantic_hash_trojan_no_user_pass():
    """Test create_semantic_hash for a trojan link with no user/pass."""
    config = "trojan://example.com:443"
    h1 = create_semantic_hash(config, 0)
    h2 = create_semantic_hash("trojan://password@example.com:443", 0)
    assert h1 is not None
    assert h1 != h2


def test_extract_host_port_vless_fallback():
    """Test extract_host_port fallback for a VLESS URI that isn't base64."""
    config = "vless://uuid@example.com:443?encryption=none#test"
    host, port = extract_host_port(config)
    assert host == "example.com"
    assert port == 443


def test_extract_host_port_ssr_not_enough_parts():
    """Test extract_host_port for SSR with not enough parts after decoding."""
    # This base64 decodes to "hostonly"
    config = "ssr://aG9zdG9ubHk="
    host, port = extract_host_port(config)
    assert host is None
    assert port is None


def test_create_semantic_hash_oversized_payload():
    """Test create_semantic_hash with oversized base64 payloads."""
    # VLESS/VMess - identifier should be None
    oversized_vless = "vless://" + "a" * 5000
    assert create_semantic_hash(oversized_vless, 0, max_decode_size=1024) is not None

    # SS - identifier should be None
    oversized_ss = "ss://" + "a" * 5000 + "@host:port"
    assert create_semantic_hash(oversized_ss, 0, max_decode_size=1024) is not None


def test_create_semantic_hash_trojan_user_and_pass():
    """Test create_semantic_hash for a trojan with user and password."""
    config = "trojan://user:pass@example.com:443"
    h = create_semantic_hash(config, 0)
    assert h is not None


def test_create_semantic_hash_trojan_only_pass():
    """Test create_semantic_hash for a trojan with only a password."""
    config = "trojan://:pass@example.com:443"
    h = create_semantic_hash(config, 0)
    assert h is not None


def test_create_semantic_hash_ss_user_pass():
    """Test create_semantic_hash for a non-standard ss link with user:pass."""
    config = "ss://user:pass@example.com:123"
    h = create_semantic_hash(config, 0)
    assert h is not None


def test_apply_tuning_no_double_slash():
    """Test apply_tuning with a config that has no double slash."""
    config = "trojan:password@example.com:443"
    tuned = apply_tuning(config, Settings())
    assert tuned == config