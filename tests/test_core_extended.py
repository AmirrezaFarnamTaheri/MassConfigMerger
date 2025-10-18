from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from configstream.core import (Proxy, ProxyTester,
                               generate_base64_subscription,
                               generate_clash_config, geolocate_proxy,
                               parse_config, run_single_proxy_test, _parse_vmess, _parse_vless, _parse_trojan, _parse_shadowsocks)


@pytest.mark.parametrize(
    "invalid_config",
    [
        "vmess://invalid-base64",  # Invalid base64
        "vless://?#",  # Missing host
        "ss://",  # Incomplete ss
        "trojan://?#",  # Incomplete trojan
        "http://invalid",  # Not a supported protocol
    ],
)
def test_parse_config_invalid(invalid_config):
    """Test that parse_config returns None for various invalid inputs."""
    assert parse_config(invalid_config) is None


@pytest.mark.asyncio
async def test_run_single_proxy_test_invalid_config():
    """Test run_single_proxy_test with an unparsable config."""
    result = await run_single_proxy_test("invalid-config-string")
    assert result is None


def test_geolocate_proxy_with_exception():
    """Test that geolocate_proxy handles exceptions gracefully."""
    mock_reader = MagicMock()
    mock_reader.city.side_effect = Exception("GeoIP DB error")

    proxy = Proxy(config="test", protocol="test", address="1.1.1.1", port=80)
    geolocate_proxy(proxy, geoip_reader=mock_reader)

    assert proxy.country == "Unknown"
    assert proxy.country_code == "XX"
    assert proxy.city == "Unknown"
    assert proxy.asn == "Unknown"


def test_geolocate_proxy_no_reader():
    """Test geolocate_proxy when no GeoIP reader is available."""
    proxy = Proxy(config="test", protocol="test", address="1.1.1.1", port=80)
    geolocate_proxy(proxy, geoip_reader=None)

    assert proxy.country == "Unknown"
    assert proxy.country_code == "XX"
    assert proxy.city == "Unknown"
    assert proxy.asn == "Unknown"


def test_generate_base64_subscription_empty():
    """Test that an empty list of proxies produces an empty subscription."""
    assert generate_base64_subscription([]) == ""


def test_generate_clash_config_empty():
    """Test that an empty list of proxies produces a valid empty Clash config."""
    result = generate_clash_config([])
    assert "proxies: []" in result


def test_generate_clash_config_with_details():
    """Test Clash config generation with various proxy details."""
    proxies = [
        Proxy(
            config="vmess://test",
            protocol="vmess",
            remarks="vmess-test",
            address="test.com",
            port=443,
            uuid="uuid",
            _details={
                "aid": 16,
                "scy": "aes-128-gcm",
                "tls": "tls",
                "net": "ws"
            },
            is_working=True,
        ),
        Proxy(
            config="ss://test",
            protocol="shadowsocks",
            remarks="ss-test",
            address="test2.com",
            port=8080,
            _details={
                "method": "aes-256-gcm",
                "password": "password"
            },
            is_working=True,
        ),
    ]
    result = generate_clash_config(proxies)
    assert "alterId: 16" in result
    assert "network: ws" in result
    assert "cipher: aes-256-gcm" in result


def test_parse_vless_no_hostname():
    """Test that _parse_vless returns None if the hostname is missing."""
    assert parse_config("vless://?#") is None


def test_parse_trojan_no_hostname():
    """Test that _parse_trojan returns None if the hostname is missing."""
    assert parse_config("trojan://?#") is None


@pytest.mark.asyncio
async def test_proxy_tester_success():
    """Test the ProxyTester with a successful connection."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_get.return_value.__aenter__.return_value = mock_response

        tester = ProxyTester()
        proxy = Proxy(
            config="http://user:pass@host:8080",
            protocol="http",
            address="host",
            port=8080,
        )
        result = await tester.test(proxy)
        assert result.is_working is True
        assert result.latency is not None


def test_generate_clash_config_no_remarks():
    """Test Clash config generation for a proxy with no remarks."""
    proxies = [
        Proxy(
            config="vless://test",
            protocol="vless",
            address="test.com",
            port=443,
            uuid="uuid",
            _details={},
            is_working=True,
        )
    ]
    result = generate_clash_config(proxies)
    assert "name: vless-test.com" in result


def test_parse_shadowsocks_invalid():
    """Test that _parse_shadowsocks returns None for an invalid config."""
    assert parse_config("ss://invalid-config") is None


@pytest.mark.asyncio
async def test_proxy_tester_failure():
    """Test the ProxyTester with a connection failure."""
    with patch(
            "aiohttp_proxy.ProxyConnector.from_url") as mock_connector, patch(
                "aiohttp.ClientSession") as mock_session:
        mock_connector.return_value.close = AsyncMock()
        mock_session.return_value.__aenter__.return_value.get.side_effect = Exception(
            "Connection failed")
        tester = ProxyTester()
        proxy = Proxy(
            config="http://user:pass@host:8080",
            protocol="http",
            address="host",
            port=8080,
        )
        result = await tester.test(proxy)
        assert result.is_working is False
        assert result.latency is None


@pytest.fixture
def working_proxies():
    return [
        Proxy(
            config="vmess://ewogICJ2IjogIjIiLAogICJwcyI6ICJqdS10dC5uYW1lIiwKICAiYWRkIjogImp1LXR0Lm5hbWUiLAogICJwb3J0IjogIjQ0MyIsCiAgImlkIjogIjAzZDAxMWYwLTM4ZTgtNGY5OS05YmY5LTUwMWQzYzdlMWY5MSIsCiAgImFpZCI6ICIwIiwKICAibmV0IjogIndzIiwKICAidHlwZSI6ICJub25lIiwKICAiaG9zdCI6ICJ3d3cuZ29vZ2xlLmNvbSIsCiAgInBhdGgiOiAiL2FsaXRhIiwKICAidGxzIjogInRscyIKfQ==",
            protocol="vmess",
            address="ju-tt.name",
            port=443,
            uuid="03d011f0-38e8-4f99-9bf9-501d3c7e1f91",
            remarks="vmess-proxy",
            is_working=True,
            _details={
                "v": "2",
                "ps": "ju-tt.name",
                "add": "ju-tt.name",
                "port": "443",
                "id": "03d011f0-38e8-4f99-9bf9-501d3c7e1f91",
                "aid": "0",
                "net": "ws",
                "type": "none",
                "host": "www.google.com",
                "path": "/alita",
                "tls": "tls",
            },
        ),
        Proxy(
            config="vless://03d011f0-38e8-4f99-9bf9-501d3c7e1f91@ju-tt.name:443?encryption=none&security=tls&type=ws&host=www.google.com&path=/alita#vless-proxy",
            protocol="vless",
            address="ju-tt.name",
            port=443,
            uuid="03d011f0-38e8-4f99-9bf9-501d3c7e1f91",
            remarks="vless-proxy",
            is_working=True,
            _details={
                "encryption": "none",
                "security": "tls",
                "type": "ws",
                "host": "www.google.com",
                "path": "/alita",
            },
        ),
        Proxy(
            config="ss://YWVzLTI1Ni1nY206Zm9vYmFy@127.0.0.1:8080#ss-proxy",
            protocol="shadowsocks",
            address="127.0.0.1",
            port=8080,
            remarks="ss-proxy",
            is_working=True,
            _details={
                "method": "aes-256-gcm",
                "password": "foobar"
            },
        ),
        Proxy(
            config="trojan://user:pass@example.com:443#trojan-proxy",
            protocol="trojan",
            address="example.com",
            port=443,
            uuid="user:pass",
            remarks="trojan-proxy",
            is_working=False,  # This one should be excluded
        ),
    ]


def test_generate_base64_subscription(working_proxies):
    """Test that only working proxies are included in the base64 output."""
    subscription = generate_base64_subscription(working_proxies)
    import base64

    decoded_sub = base64.b64decode(subscription).decode()

    # Should contain the 3 working proxies
    assert "vmess://" in decoded_sub
    assert "vless://" in decoded_sub
    assert "ss://" in decoded_sub
    # Should NOT contain the non-working trojan proxy
    assert "trojan://" not in decoded_sub

    lines = decoded_sub.splitlines()
    assert len(lines) == 3


def test_generate_clash_config(working_proxies):
    """Test Clash config generation with various protocols."""
    clash_config_str = generate_clash_config(working_proxies)
    clash_config = yaml.safe_load(clash_config_str)

    assert "proxies" in clash_config
    assert "proxy-groups" in clash_config

    proxies = clash_config["proxies"]
    # Should only have the 3 working proxies
    assert len(proxies) == 3

    vmess = next(p for p in proxies if p["type"] == "vmess")
    vless = next(p for p in proxies if p["type"] == "vless")
    ss = next(p for p in proxies if p["type"] == "shadowsocks")

    # VMess specific checks
    assert vmess["name"] == "vmess-proxy"
    assert vmess["server"] == "ju-tt.name"
    assert vmess["tls"] is True
    assert vmess["network"] == "ws"

    # VLESS specific checks
    assert vless["name"] == "vless-proxy"
    assert vless["uuid"] == "03d011f0-38e8-4f99-9bf9-501d3c7e1f91"

    # Shadowsocks specific checks
    assert ss["name"] == "ss-proxy"
    assert ss["cipher"] == "aes-256-gcm"
    assert ss["password"] == "foobar"

    # Check proxy group
    proxy_group = clash_config["proxy-groups"][0]
    assert proxy_group["name"] == "🚀 ConfigStream"
    assert len(proxy_group["proxies"]) == 3
    assert "vmess-proxy" in proxy_group["proxies"]


def test_generate_clash_config_no_remarks(working_proxies):
    """Test that a fallback name is generated when remarks are missing."""
    working_proxies[0].remarks = ""
    clash_config_str = generate_clash_config(working_proxies)
    clash_config = yaml.safe_load(clash_config_str)

    vmess_proxy = clash_config["proxies"][0]
    assert vmess_proxy["name"] == "vmess-ju-tt.name"


def test_geolocate_proxy_no_reader():
    """Test graceful handling when GeoIP reader is not available."""
    proxy = Proxy(config="", protocol="test", address="1.1.1.1", port=443)
    geolocated_proxy = geolocate_proxy(proxy, geoip_reader=None)

    assert geolocated_proxy.country == "Unknown"
    assert geolocated_proxy.country_code == "XX"
    assert geolocated_proxy.city == "Unknown"
    assert geolocated_proxy.asn == "Unknown"


def test_geolocate_proxy_lookup_error():
    """Test graceful handling when GeoIP lookup fails."""
    proxy = Proxy(config="", protocol="test", address="1.1.1.1", port=443)

    # Mock the reader to raise an exception
    mock_reader = MagicMock()
    mock_reader.city.side_effect = Exception("Test GeoIP Error")

    geolocated_proxy = geolocate_proxy(proxy, geoip_reader=mock_reader)

    assert geolocated_proxy.country == "Unknown"
    assert geolocated_proxy.country_code == "XX"
    assert geolocated_proxy.city == "Unknown"
    assert geolocated_proxy.asn == "Unknown"


@patch("configstream.core._parse_vmess", side_effect=Exception("mocked error"))
def test_parse_config_general_exception(mock_parse_vmess):
    """Test that parse_config handles unexpected exceptions."""
    assert parse_config("vmess://anything") is None


def test_parse_vmess_invalid_json():
    """Test that _parse_vmess handles invalid JSON."""
    # This base64 string decodes to invalid JSON
    invalid_vmess = "vmess://ewogICJ2IjogIjIiLAogICJwc"
    assert parse_config(invalid_vmess) is None


def test_parse_shadowsocks_no_at_symbol():
    """Test that _parse_shadowsocks returns None if there is no @ symbol."""
    assert parse_config("ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ") is None


def test_generate_clash_config_with_non_working_proxy():
    """Test that non-working proxies are excluded from Clash config."""
    proxies = [
        Proxy(
            config="vless://test",
            protocol="vless",
            address="test.com",
            port=443,
            uuid="uuid",
            is_working=False,  # This proxy should be ignored
        )
    ]
    result = generate_clash_config(proxies)
    assert "proxies: []" in result


def test_parse_vmess_invalid_base64():
    """Test that _parse_vmess returns None for invalid base64."""
    # This is not a valid base64 string
    invalid_config = "vmess://invalid-base64-string"
    assert _parse_vmess(invalid_config) is None


def test_parse_vless_no_hostname():
    """Test that _parse_vless returns None when the hostname is missing."""
    # This config has no hostname
    invalid_config = "vless://?encryption=none"
    assert _parse_vless(invalid_config) is None


def test_parse_trojan_no_hostname():
    """Test that _parse_trojan returns None when the hostname is missing."""
    # This config has no hostname
    invalid_config = "trojan://?peer=example.com"
    assert _parse_trojan(invalid_config) is None


def test_parse_shadowsocks_no_at_symbol():
    """Test that _parse_shadowsocks returns None when there is no '@' symbol."""
    # This config is missing the '@' separator
    invalid_config = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ="
    assert _parse_shadowsocks(invalid_config) is None


def test_parse_shadowsocks_invalid_base64():
    """Test that _parse_shadowsocks returns None for invalid base64 in the user info."""
    # The user info part is not valid base64
    invalid_config = "ss://invalid-base64@example.com:8080"
    assert _parse_shadowsocks(invalid_config) is None
