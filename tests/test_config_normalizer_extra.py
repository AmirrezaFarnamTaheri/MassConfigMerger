from __future__ import annotations

import base64
import pytest
from unittest.mock import patch
from configstream.config import Settings
from configstream.core.config_normalizer import (
    extract_host_port,
    _normalize_url,
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


def test_apply_tuning_invalid_uri():
    """Test that apply_tuning returns the original config on ValueError."""
    config = "http://[::1"  # Malformed IPv6 URI
    settings = Settings()
    # This should trigger a ValueError and return the original config
    assert apply_tuning(config, settings) == config




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


def test_apply_tuning_no_double_slash():
    """Test apply_tuning with a config that has no double slash."""
    config = "trojan:password@example.com:443"
    tuned = apply_tuning(config, Settings())
    assert tuned == config