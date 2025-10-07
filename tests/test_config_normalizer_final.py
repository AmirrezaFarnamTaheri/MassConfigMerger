from __future__ import annotations

from unittest.mock import patch
import pytest

from configstream.core.config_normalizer import (
    extract_host_port,
    create_semantic_hash,
)

@patch("configstream.core.config_normalizer.logging.debug")
def test_extract_host_port_vless_fallback_failure(mock_logging_debug):
    """Test that the vless host/port extraction fallback logs on failure."""
    # This config is invalid base64 and also not a valid URI with host/port
    config = "vless://!!!###"
    extract_host_port(config)
    mock_logging_debug.assert_called_once_with(
        "extract_host_port vmess/vless fallback failed for: %s", config
    )

@patch("configstream.core.config_normalizer.extract_host_port", return_value=(None, None))
def test_create_semantic_hash_no_host_port(mock_extract_host_port):
    """Test create_semantic_hash when host and port cannot be extracted."""
    config = "vless://some-id@?type=ws"
    # The hash should be based on the normalized config string
    result_hash = create_semantic_hash(config, 0)
    assert result_hash is not None
    assert isinstance(result_hash, str)
    mock_extract_host_port.assert_called_once()

def test_create_semantic_hash_trojan_password_only():
    """Test create_semantic_hash for a trojan link with only a password."""
    # The parser should handle this gracefully. The identifier becomes the password.
    config = "trojan://:password@example.com:443"
    result_hash = create_semantic_hash(config, 0)
    assert result_hash is not None
    assert isinstance(result_hash, str)

def test_create_semantic_hash_ss_from_userinfo():
    """Test create_semantic_hash for an ss link with credentials in userinfo."""
    config = "ss://aes-256-gcm:password@example.com:8443"
    result_hash = create_semantic_hash(config, 0)
    # The hash should be based on password@host:port
    expected_key = "password@example.com:8443"
    import hashlib
    expected_hash = hashlib.sha256(expected_key.encode()).hexdigest()[:16]
    assert result_hash == expected_hash