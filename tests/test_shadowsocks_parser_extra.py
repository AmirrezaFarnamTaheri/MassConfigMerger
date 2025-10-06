from __future__ import annotations

import base64
import pytest

from massconfigmerger.core.parsers.shadowsocks import ShadowsocksParser


@pytest.mark.parametrize(
    "malformed_base64_content",
    [
        "method:pass@host",  # Missing port
        "method@host:port",  # Missing password
        "pass@host:port",    # Missing method
    ],
)
def test_parse_malformed_base64(malformed_base64_content: str):
    """Test that the ss parser returns None for malformed base64 content."""
    encoded_content = base64.b64encode(malformed_base64_content.encode()).decode()
    config = f"ss://{encoded_content}"
    parser = ShadowsocksParser(config, 0)
    assert parser.parse() is None


def test_parse_missing_components():
    """Test that the ss parser returns None if essential components are missing."""
    # This format is not standard but supported as a fallback.
    # We test the case where the hostname is missing.
    config = "ss://YWVzLTI1Ni1nY206dGVzdA==@:443"  # Empty hostname
    parser = ShadowsocksParser(config, 0)
    assert parser.parse() is None