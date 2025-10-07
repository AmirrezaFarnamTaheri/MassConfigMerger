from __future__ import annotations

from unittest.mock import patch
import pytest

from configstream.core.config_normalizer import (
    extract_host_port,
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