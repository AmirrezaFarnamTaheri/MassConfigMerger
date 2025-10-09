from __future__ import annotations

import base64
import pytest

from configstream.core.parsers.shadowsocks import ShadowsocksParser
from configstream.exceptions import ParserError


@pytest.mark.parametrize(
    "malformed_base64_content",
    [
        "method:pass@host",  # Missing port
        "method@host:port",  # Missing password
        "pass@host:port",    # Missing method
    ],
)
def test_parse_malformed_base64(malformed_base64_content: str):
    """Test that the ss parser raises ParserError for malformed base64 content."""
    encoded_content = base64.b64encode(
        malformed_base64_content.encode()).decode()
    config = f"ss://{encoded_content}"
    parser = ShadowsocksParser(config, 0)
    with pytest.raises(ParserError):
        parser.parse()


def test_get_identifier_with_password_field():
    """Test get_identifier when password is in the password field."""
    uri = "ss://aes-256-gcm:password@1.2.3.4:1234"
    parser = ShadowsocksParser(uri, 0)
    assert parser.get_identifier() == "password"


def test_get_identifier_with_base64_userinfo():
    """Test get_identifier with base64 encoded userinfo."""
    user_info = base64.urlsafe_b64encode(b"aes-256-gcm:password123").decode()
    uri = f"ss://{user_info}@1.2.3.4:1234"
    parser = ShadowsocksParser(uri, 0)
    assert parser.get_identifier() == "password123"


def test_get_identifier_with_invalid_base64_userinfo():
    """Test get_identifier with invalid base64 userinfo falls back."""
    # The fallback will also fail here, so we expect None
    uri = "ss://invalid-base64@1.2.3.4:1234"
    parser = ShadowsocksParser(uri, 0)
    assert parser.get_identifier() is None


def test_get_identifier_from_full_uri_encoding():
    """Test get_identifier from a fully encoded URI."""
    encoded = base64.urlsafe_b64encode(b"aes-256-gcm:my-secret-pw@5.6.7.8:999").decode()
    uri = f"ss://{encoded}"
    parser = ShadowsocksParser(uri, 0)
    assert parser.get_identifier() == "my-secret-pw"


def test_get_identifier_fallback_failure():
    """Test get_identifier returns None when all parsing methods fail."""
    encoded = base64.urlsafe_b64encode(b"this-is-not-a-valid-ss-config").decode()
    uri = f"ss://{encoded}"
    parser = ShadowsocksParser(uri, 0)
    assert parser.get_identifier() is None


def test_parse_missing_components():
    """Test that the ss parser raises ParserError if essential components are missing."""
    # This format is not standard but supported as a fallback.
    # We test the case where the hostname is missing.
    config = "ss://YWVzLTI1Ni1nY206dGVzdA==@:443"  # Empty hostname
    parser = ShadowsocksParser(config, 0)
    with pytest.raises(ParserError):
        parser.parse()
