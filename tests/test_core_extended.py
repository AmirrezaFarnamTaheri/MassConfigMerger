from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.core import (Proxy, ProxyTester, generate_clash_config,
                               geolocate_proxy, parse_config,
                               run_single_proxy_test)

# --- Tests for ProxyTester and run_single_proxy_test ---


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
@patch("aiohttp_proxy.ProxyConnector.from_url")
async def test_proxy_tester_success(mock_from_url, mock_session_class):
    """Test ProxyTester with a successful connection."""
    mock_connector = AsyncMock()
    mock_from_url.return_value = mock_connector

    mock_session_instance = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 204

    get_context_manager = AsyncMock()
    get_context_manager.__aenter__.return_value = mock_response

    # session.get is a regular method that returns an async context manager
    mock_session_instance.get = MagicMock(return_value=get_context_manager)

    session_context_manager = AsyncMock()
    session_context_manager.__aenter__.return_value = mock_session_instance
    mock_session_class.return_value = session_context_manager

    proxy = Proxy(config="test_config", protocol="test", address="localhost", port=1234)
    tester = ProxyTester()
    result_proxy = await tester.test(proxy)

    assert result_proxy.is_working is True
    assert result_proxy.latency is not None
    mock_connector.close.assert_called_once()


@pytest.mark.asyncio
@patch("aiohttp_proxy.ProxyConnector.from_url")
@patch("aiohttp.ClientSession", side_effect=Exception("Connection failed"))
async def test_proxy_tester_failure(mock_session, mock_from_url):
    """Test ProxyTester with a failed connection."""
    mock_connector = AsyncMock()
    mock_from_url.return_value = mock_connector

    proxy = Proxy(config="test_config", protocol="test", address="localhost", port=1234)
    tester = ProxyTester()
    result_proxy = await tester.test(proxy)

    assert result_proxy.is_working is False
    assert result_proxy.latency is None
    mock_connector.close.assert_called_once()


@pytest.mark.asyncio
@patch("configstream.core.parse_config")
@patch("configstream.core.ProxyTester.test")
async def test_run_single_proxy_test_entrypoint(mock_test, mock_parse):
    """Test the run_single_proxy_test entrypoint function."""
    mock_parse.return_value = Proxy(config="c", protocol="p", address="a", port=1)
    await run_single_proxy_test("test_config")
    mock_parse.assert_called_once_with("test_config")
    mock_test.assert_called_once()


# --- Tests for geolocate_proxy ---


def test_geolocate_proxy_no_reader():
    """Test geolocation when the GeoIP reader is not available."""
    proxy = Proxy(config="c", protocol="p", address="a", port=1)
    geolocate_proxy(proxy, geoip_reader=None)
    assert proxy.country_code == "XX"
    assert proxy.asn == "Unknown"


def test_geolocate_proxy_success():
    """Test successful geolocation."""
    mock_reader = MagicMock()
    mock_response = MagicMock()
    mock_response.country.name = "Test Country"
    mock_response.country.iso_code = "TC"
    mock_response.city.name = "Test City"
    mock_response.autonomous_system_number = 123
    mock_reader.city.return_value = mock_response

    proxy = Proxy(config="c", protocol="p", address="8.8.8.8", port=1)
    geolocate_proxy(proxy, geoip_reader=mock_reader)

    assert proxy.country == "Test Country"
    assert proxy.country_code == "TC"
    assert proxy.city == "Test City"
    assert proxy.asn == "AS123"


def test_geolocate_proxy_lookup_fails():
    """Test geolocation when the lookup raises an exception."""
    mock_reader = MagicMock()
    mock_reader.city.side_effect = Exception("Lookup failed")

    proxy = Proxy(config="c", protocol="p", address="a", port=1)
    geolocate_proxy(proxy, geoip_reader=mock_reader)

    assert proxy.country_code == "XX"
    assert proxy.asn == "Unknown"


# --- Tests for generate_clash_config ---


def test_generate_clash_config_all_protocols():
    """Test Clash config generation with different proxy protocols."""
    proxies = [
        Proxy(
            config="c1",
            protocol="vmess",
            address="vmess.host",
            port=1,
            uuid="vmid",
            remarks="vmess_remark",
            is_working=True,
            _details={"net": "ws", "tls": "tls"},
        ),
        Proxy(
            config="c2",
            protocol="shadowsocks",
            address="ss.host",
            port=2,
            remarks="ss_remark",
            is_working=True,
            _details={"method": "aes-256-gcm", "password": "pass"},
        ),
        Proxy(
            config="c3",
            protocol="trojan",
            address="trojan.host",
            port=3,
            uuid="trojanid",
            remarks="trojan_remark",
            is_working=True,
        ),
        Proxy(
            config="c4",
            protocol="vless",
            address="vless.host",
            port=4,
            uuid="vlessid",
            remarks="vless_remark",
            is_working=False,
        ),  # Should be excluded
    ]

    clash_config_str = generate_clash_config(proxies)
    assert "vmess_remark" in clash_config_str
    assert "ss_remark" in clash_config_str
    assert "trojan_remark" in clash_config_str
    assert "vless_remark" not in clash_config_str  # because is_working=False

    import yaml

    clash_config = yaml.safe_load(clash_config_str)

    assert len(clash_config["proxies"]) == 3
    assert clash_config["proxies"][0]["network"] == "ws"
    assert clash_config["proxies"][0]["tls"] is True
    assert clash_config["proxies"][1]["cipher"] == "aes-256-gcm"
    assert clash_config["proxies"][1]["password"] == "pass"
    assert "🚀 ConfigStream" in clash_config["proxy-groups"][0]["name"]


def test_parse_invalid_config():
    """Test that invalid or unparseable configs return None."""
    assert parse_config("invalid-protocol://some-data") is None
    assert parse_config("vmess://invalid-base64") is None
    assert parse_config("ss://invalid-format") is None
