from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from configstream.models import Proxy
from configstream.core import (ProxyTester, parse_config, run_single_proxy_test)
from configstream.output import (generate_base64_subscription,
                                 generate_clash_config)


@pytest.mark.parametrize(
    "invalid_config",
    [
        "invalid://invalid",  # Not a real proxy protocol
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
            details={
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
            details={
                "method": "aes-256-gcm",
                "password": "password"
            },
            is_working=True,
        ),
    ]
    result = generate_clash_config(proxies)
    assert "name: vmess-test" in result
    assert "server: test.com" in result
    assert "name: ss-test" in result
    assert "server: test2.com" in result


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
        assert result.success is True
        assert result.latency_ms is not None


@pytest.mark.asyncio
async def test_proxy_tester_failure():
    """Test the ProxyTester with a connection failure."""
    with patch(
            "aiohttp.ClientSession.get",
            side_effect=Exception("Connection failed")):
        tester = ProxyTester()
        proxy = Proxy(
            config="http://user:pass@host:8080",
            protocol="http",
            address="host",
            port=8080,
        )
        result = await tester.test(proxy)
        assert result.success is False
        assert result.latency_ms is None