from __future__ import annotations
import base64
from unittest.mock import patch

import pytest

from configstream.core.utils import is_valid_config, parse_configs_from_text


@pytest.mark.parametrize(
    "link, expected",
    [
        ("ssr://invalid-b64", False),  # Invalid base64
        ("naive://user:pass@example.com:443", True),
        ("hy2://pass@example.com:443", True),
        ("vless://uuid@example.com:443", True),
        ("trojan://pass@example.com:443", True),
        ("ss://method:pass@example.com:443", True),
        ("http://example.com:80", True),
        ("wireguard://config", True),
        # Edge cases
            ("invalid-proto://", False), # Fallback case
        ("ss://user-only@host:port", False), # Invalid ss format
    ],
)
def test_is_valid_config_coverage(link, expected):
    """Test edge cases and various protocols for is_valid_config."""
    # The ss:// with userinfo is not standard and requires this for parsing
    from urllib.parse import uses_netloc
    if "ss" not in uses_netloc:
        uses_netloc.append("ss")

    assert is_valid_config(link) == expected

    if "ss" in uses_netloc:
        uses_netloc.remove("ss")

def test_parse_configs_from_text_oversized_b64():
    """Test that oversized base64 lines are skipped."""
    # Create a base64 string that is longer than the max size
    long_string = "a" * 5000
    b64_string = base64.urlsafe_b64encode(long_string.encode()).decode()
    text = f"some text\n{b64_string}\nmore text"

    with patch("configstream.core.utils.MAX_DECODE_SIZE", 4000):
        configs = parse_configs_from_text(text)
        assert len(configs) == 0

def test_parse_configs_from_text_invalid_b64():
    """Test that invalid base64 lines are skipped."""
    text = "some text\ninvalid-base64-string\nmore text"
    configs = parse_configs_from_text(text)
    assert len(configs) == 0