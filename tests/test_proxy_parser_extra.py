from __future__ import annotations

import binascii
import json
from unittest.mock import patch

import pytest
from configstream.core.proxy_parser import ProxyParser


@pytest.mark.parametrize(
    "exception_to_raise",
    [
        ValueError("Test ValueError"),
        binascii.Error("Test binascii.Error"),
        json.JSONDecodeError("Test JSONDecodeError", "", 0),
    ],
)
@patch("configstream.core.parsers.vmess.VmessParser.parse")
@patch("configstream.core.proxy_parser.logging.debug")
def test_config_to_clash_proxy_exception_handling(
    mock_logging_debug, mock_vmess_parse, exception_to_raise
):
    """Test that config_to_clash_proxy handles exceptions from parsers."""
    mock_vmess_parse.side_effect = exception_to_raise
    parser = ProxyParser()

    result = parser.config_to_clash_proxy("vmess://test")

    assert result is None
    mock_logging_debug.assert_called_once()
    # Check that the log message contains the expected text
    args, _ = mock_logging_debug.call_args
    assert "config_to_clash_proxy failed" in args[0]
    assert "Test" in str(args[2])