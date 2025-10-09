from __future__ import annotations

import base64
import pytest

from configstream.core.parsers.ssr import SsrParser


def test_parse_ssr_malformed_main_part():
    """Test parsing an SSR link with a malformed main part."""
    # This base64 string decodes to "server:port:proto:method:obfs" (5 parts, not 6)
    malformed_main = base64.urlsafe_b64encode(
        b"server:port:proto:method:obfs").decode()
    config = f"ssr://{malformed_main}"
    parser = SsrParser(config, 0)
    assert parser.parse() is None


def test_parse_ssr_invalid_base64_in_param():
    """Test that the ssr parser handles invalid base64 in optional params."""
    main_part = "example.com:443:auth_aes128_md5:aes-128-cfb:http_simple:"
    password_b64 = base64.urlsafe_b64encode(b"password").decode()

    # "not-base64" is not valid base64
    query = "/?obfsparam=not-base64"

    string_to_encode = f"{main_part}{password_b64}{query}"
    encoded_config = base64.urlsafe_b64encode(
        string_to_encode.encode()).decode()
    config = f"ssr://{encoded_config}"

    parser = SsrParser(config, 0)
    result = parser.parse()

    assert result is not None
    # The parser should fall back to using the raw string
    assert result["obfs-param"] == "not-base64"
