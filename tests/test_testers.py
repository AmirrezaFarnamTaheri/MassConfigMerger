from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import web

from configstream.core import Proxy
from configstream.testers import SingBoxTester


@pytest.mark.asyncio
async def test_singbox_tester_success(aiohttp_client):
    """
    Test the SingBoxTester with a successful proxy connection.
    This test mocks the SingBoxProxy and the test URL endpoint.
    """

    # Arrange
    async def handler(request):
        # This handler will be called by the tester through the mock proxy
        return web.Response(status=204)

    app = web.Application()
    app.router.add_get("/generate_204", handler)
    client = await aiohttp_client(app)

    test_urls = {"primary": str(client.server.make_url("/generate_204"))}

    # Patch the config to use our mock server URL
    with patch("configstream.testers.ProxyConfig.TEST_URLS", test_urls), patch(
        "configstream.testers.SingBoxProxy"
    ) as mock_singbox_proxy:

        # Configure the mock SingBoxProxy
        mock_sb_instance = AsyncMock()
        mock_sb_instance.start = AsyncMock()
        mock_sb_instance.stop = AsyncMock()
        # This is the key: the tester will use this URL to connect to the proxy
        mock_sb_instance.http_proxy_url = str(client.server.make_url("/"))
        mock_singbox_proxy.return_value = mock_sb_instance

        tester = SingBoxTester()
        proxy = Proxy(config="test_config", protocol="vmess", address="1.1.1.1", port=443)

        # Act
        tested_proxy = await tester.test(proxy)

    # Assert
    assert tested_proxy.is_working is True
    assert tested_proxy.latency is not None and tested_proxy.latency > 0
    assert not tested_proxy.security_issues


@pytest.mark.asyncio
async def test_singbox_tester_failure_masked():
    """
    Test the SingBoxTester with a failed connection and masked errors.
    """
    # Arrange
    with patch("configstream.testers.SingBoxProxy") as mock_singbox_proxy:
        mock_sb_instance = AsyncMock()
        mock_sb_instance.start = AsyncMock(side_effect=Exception("Connection refused"))
        mock_sb_instance.stop = AsyncMock()
        mock_singbox_proxy.return_value = mock_sb_instance

        tester = SingBoxTester()
        tester.config.MASK_SENSITIVE_DATA = True
        proxy = Proxy(config="test_config", protocol="vmess", address="1.1.1.1", port=443)

        # Act
        tested_proxy = await tester.test(proxy)

    # Assert
    assert tested_proxy.is_working is False
    assert "Connection failed: [MASKED]" in tested_proxy.security_issues[0]


@pytest.mark.asyncio
async def test_singbox_tester_failure_unmasked():
    """
    Test the SingBoxTester with a failed connection and unmasked errors.
    """
    # Arrange
    with patch("configstream.testers.SingBoxProxy") as mock_singbox_proxy:
        mock_sb_instance = AsyncMock()
        mock_sb_instance.start = AsyncMock(side_effect=Exception("Connection refused"))
        mock_sb_instance.stop = AsyncMock()
        mock_singbox_proxy.return_value = mock_sb_instance

        tester = SingBoxTester()
        tester.config.MASK_SENSITIVE_DATA = False
        proxy = Proxy(config="test_config", protocol="vmess", address="1.1.1.1", port=443)

        # Act
        tested_proxy = await tester.test(proxy)

    # Assert
    assert tested_proxy.is_working is False
    assert "Connection refused" in tested_proxy.security_issues[0]
