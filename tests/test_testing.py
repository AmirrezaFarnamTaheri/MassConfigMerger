from __future__ import annotations

import copy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from configstream.core import Proxy
from configstream.testing import process_and_test_proxies, SingBoxWorker


@pytest.fixture
def mock_progress():
    """Fixture for a mock Rich Progress object."""
    return MagicMock()


@pytest.fixture
def sample_proxies():
    """Fixture for a list of sample Proxy objects."""
    return [
        Proxy(config="vless://test1@test.com:443#Working", protocol="vless", address="1.1.1.1", remarks="Working"),
        Proxy(config="trojan://test2@test.com:443#NotWorking", protocol="trojan", address="8.8.8.8", remarks="NotWorking"),
        Proxy(config="ss://test3@test.com:443#Secure", protocol="shadowsocks", address="9.9.9.9", remarks="Secure"),
    ]


@pytest.mark.asyncio
async def test_process_and_test_proxies_happy_path(mock_progress, sample_proxies):
    """
    Tests the main proxy processing and testing pipeline with mock workers.
    """
    async def side_effect(proxy, worker):
        # This simplified side effect correctly simulates the test outcomes.
        new_proxy = copy.deepcopy(proxy)
        if "NotWorking" in new_proxy.remarks:
            new_proxy.is_working = False
            new_proxy.is_secure = False
        else:
            new_proxy.is_working = True
            new_proxy.is_secure = True
            new_proxy.latency = 100 if "Working" in new_proxy.remarks else 50
        return new_proxy

    with patch("configstream.testing.test_and_geolocate_proxy", side_effect=side_effect) as mock_test_and_geolocate:
        results = await process_and_test_proxies(sample_proxies, mock_progress, max_workers=2)

        assert len(results) == 3
        working_proxies = [p for p in results if p.is_working and p.is_secure]
        assert len(working_proxies) == 2


@pytest.mark.asyncio
@patch('aiohttp.ClientSession')
async def test_singbox_worker_test_proxy_success(mock_session_class):
    """
    Tests the SingBoxWorker's test_proxy method for a successful connection.
    """
    # Configure the mock response for aiohttp
    mock_response = AsyncMock()
    mock_response.status = 204
    mock_response.json.return_value = {"rating": "Probably Okay"}
    mock_response.text.return_value = "Example Domain"

    # Configure the mock session context manager
    mock_session = mock_session_class.return_value
    mock_session.get.return_value.__aenter__.return_value = mock_response

    # Configure the SingBoxProxy mock
    mock_singbox_instance = MagicMock()
    mock_singbox_instance.start = AsyncMock()
    mock_singbox_instance.stop = AsyncMock()
    mock_singbox_instance.http_proxy_url = "http://127.0.0.1:2080"

    with patch("configstream.testing.SingBoxProxy", return_value=mock_singbox_instance):
        worker = SingBoxWorker()
        proxy_instance = Proxy(config="vless://test@test.com:443", address="1.1.1.1")

        await worker.test_proxy(proxy_instance)

        assert proxy_instance.is_working is True
        assert proxy_instance.is_secure is True
        assert proxy_instance.latency is not None
        mock_singbox_instance.start.assert_awaited_once()
        mock_singbox_instance.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_singbox_worker_test_proxy_failure():
    """
    Tests the SingBoxWorker's test_proxy method for a failed connection.
    """
    mock_singbox_instance = MagicMock()
    mock_singbox_instance.start = AsyncMock(side_effect=Exception("Failed to start"))
    mock_singbox_instance.stop = AsyncMock()

    with patch("configstream.testing.SingBoxProxy", return_value=mock_singbox_instance):
        worker = SingBoxWorker()
        proxy_instance = Proxy(config="vless://fail@test.com:443", address="1.1.1.1")

        await worker.test_proxy(proxy_instance)

        assert proxy_instance.is_working is False
        assert any("Failed to start" in issue for issue in proxy_instance.security_issues)
        mock_singbox_instance.stop.assert_awaited_once()