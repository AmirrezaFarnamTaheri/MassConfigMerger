import pytest
import base64
from configstream.core.parsers.ssr import SsrParser


def test_ssr_parser_invalid_udpport():
    """Test SSR parser with a non-integer udpport to cover the ValueError except block."""
    main_part = "127.0.0.1:8080:auth_sha1_v4:aes-256-cfb:http_simple:" + base64.urlsafe_b64encode(b"password").decode()
    decoded_string = main_part + "/?udpport=abc"
    encoded_payload = base64.urlsafe_b64encode(decoded_string.encode()).decode()
    uri = f"ssr://{encoded_payload}"

    parser = SsrParser(uri, 0)
    result = parser.parse()

    assert result is not None
    assert "udpport" not in result


def test_ssr_parser_non_base64_remarks():
    """Test SSR parser with a remarks parameter that is not base64 encoded."""
    main_part = "127.0.0.1:8080:auth_sha1_v4:aes-256-cfb:http_simple:" + base64.urlsafe_b64encode(b"password").decode()
    decoded_string = main_part + "/?remarks=MyRawRemark"
    encoded_payload = base64.urlsafe_b64encode(decoded_string.encode()).decode()
    uri = f"ssr://{encoded_payload}"

    parser = SsrParser(uri, 1)
    result = parser.parse()

    assert result is not None
    assert result["name"] == "MyRawRemark"


def test_ssr_parser_with_uot_param():
    """Test SSR parser with the 'uot' parameter."""
    main_part = "127.0.0.1:8080:auth_sha1_v4:aes-256-cfb:http_simple:" + base64.urlsafe_b64encode(b"password").decode()
    decoded_string = main_part + "/?uot=1"
    encoded_payload = base64.urlsafe_b64encode(decoded_string.encode()).decode()
    uri = f"ssr://{encoded_payload}"

    parser = SsrParser(uri, 2)
    result = parser.parse()

    assert result is not None
    assert "uot" in result
    assert result["uot"] == "1"

def test_ssr_parser_invalid_base64_main():
    """Test SSR parser with invalid base64 in the main part of the URI."""
    uri = "ssr://invalid-base64-string"
    parser = SsrParser(uri, 3)
    result = parser.parse()
    assert result is None


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
