from __future__ import annotations

import base64

from configstream.core.proxy_parser import ProxyParser


def test_parse_ss_base64_encoded():
    """Test parsing of a base64-encoded Shadowsocks link."""
    parser = ProxyParser()
    # Encoded: "aes-256-gcm:password@example.com:8888"
    encoded_part = "YWVzLTI1Ni1nY206cGFzc3dvcmRAZXhhbXBsZS5jb206ODg4OA=="
    link = f"ss://{encoded_part}#Test-SS-b64"

    proxy = parser.config_to_clash_proxy(link)

    assert proxy is not None
    assert proxy["name"] == "Test-SS-b64"
    assert proxy["type"] == "ss"
    assert proxy["server"] == "example.com"
    assert proxy["port"] == 8888
    assert proxy["cipher"] == "aes-256-gcm"
    assert proxy["password"] == "password"


def test_parse_ss_userinfo():
    """Test parsing of a Shadowsocks link with userinfo.

    Note: This branch is likely dead code in the application, as 'ss' is not
    registered as a scheme that uses a netloc. We register it here temporarily
    to achieve test coverage before refactoring.
    """
    from urllib.parse import uses_netloc

    if "ss" not in uses_netloc:
        uses_netloc.append("ss")

    parser = ProxyParser()
    link = "ss://aes-256-gcm:password@example.com:8888#Test-SS-userinfo"

    proxy = parser.config_to_clash_proxy(link)

    assert proxy is not None
    assert proxy["name"] == "Test-SS-userinfo"
    assert proxy["type"] == "ss"
    assert proxy["server"] == "example.com"
    assert proxy["port"] == 8888
    assert proxy["cipher"] == "aes-256-gcm"
    assert proxy["password"] == "password"

    if "ss" in uses_netloc:
        uses_netloc.remove("ss")


def test_parse_fallback_http():
    """Test the fallback parser for an unknown scheme."""
    parser = ProxyParser()
    link = "unknown://user:pass@example.com:1234#fallback"
    proxy = parser.config_to_clash_proxy(link)
    assert proxy is not None
    assert proxy["name"] == "fallback"
    assert proxy["type"] == "http"
    assert proxy["server"] == "example.com"
    assert proxy["port"] == 1234


def test_parse_fallback_socks():
    """Test the fallback parser for a socks-like scheme."""
    parser = ProxyParser()
    link = "socksy-protocol://user:pass@example.com:1234#fallback-socks"
    proxy = parser.config_to_clash_proxy(link, protocol="socks")
    assert proxy is not None
    assert proxy["name"] == "fallback-socks"
    assert proxy["type"] == "socks5"
    assert proxy["server"] == "example.com"
    assert proxy["port"] == 1234


def test_parse_fallback_invalid():
    """Test that the fallback parser returns None for invalid URLs."""
    parser = ProxyParser()
    link = "unknown://nodata"
    proxy = parser.config_to_clash_proxy(link)
    assert proxy is None


def test_parse_naive_invalid():
    """Test that _parse_naive returns None for an invalid link."""
    parser = ProxyParser()
    link = "naive://user:pass@nohost"
    proxy = parser.config_to_clash_proxy(link)
    assert proxy is None


def test_parse_tuic_invalid():
    """Test that _parse_tuic returns None for an invalid link."""
    parser = ProxyParser()
    link = "tuic://uuid:pw@nohost"
    proxy = parser.config_to_clash_proxy(link)
    assert proxy is None


def test_ssr_non_b64_password():
    """Test SSR parsing where password is not base64 encoded."""
    raw = "example.com:443:origin:aes-128-gcm:plain:not-b64-pass"
    b64 = base64.urlsafe_b64encode(raw.encode()).decode().strip("=")
    link = f"ssr://{b64}"
    proxy = ProxyParser().config_to_clash_proxy(link)
    assert proxy["password"] == "not-b64-pass"


def test_ssr_non_b64_params():
    """Test SSR parsing where obfs and proto params are not base64 encoded."""
    raw = (
        "example.com:443:origin:aes-128-gcm:plain:cGFzcw==/"
        "?obfsparam=salt&protoparam=auth"
    )
    b64 = base64.urlsafe_b64encode(raw.encode()).decode().strip("=")
    link = f"ssr://{b64}"
    proxy = ProxyParser().config_to_clash_proxy(link)
    assert proxy["obfs-param"] == "salt"
    assert proxy["protocol-param"] == "auth"


def test_parse_vmess_fallback():
    """Test the fallback parsing logic for vmess."""
    from urllib.parse import uses_netloc

    if "vmess" not in uses_netloc:
        uses_netloc.append("vmess")

    parser = ProxyParser()
    # This link will fail the initial base64 decoding and trigger the fallback parser.
    link = "vmess://a-non-base64-string@server.com:1234?type=ws&aid=2#VmessFallback"

    proxy = parser.config_to_clash_proxy(link)

    assert proxy is not None
    assert proxy["name"] == "VmessFallback"
    assert proxy["server"] == "server.com"
    assert proxy["port"] == 1234
    assert proxy["uuid"] == "a-non-base64-string"
    assert proxy["alterId"] == 2
    assert proxy["network"] == "ws"

    if "vmess" in uses_netloc:
        uses_netloc.remove("vmess")
