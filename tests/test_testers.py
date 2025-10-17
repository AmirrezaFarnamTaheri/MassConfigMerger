import pytest
from unittest.mock import AsyncMock, patch
from aiohttp import web

from src.configstream.testers import SingBoxTester
from src.configstream.core import Proxy


@pytest.mark.asyncio
async def test_singbox_tester_success(aiohttp_client):
    """Test the SingBoxTester with a successful proxy test."""
    async def handler(request):
        return web.Response(status=204)

    app = web.Application()
    app.router.add_get("/generate_204", handler)
    client = await aiohttp_client(app)

    with patch("src.configstream.testers.SingBoxProxy") as mock_singbox_proxy:
        mock_sb_instance = AsyncMock()
        mock_sb_instance.start = AsyncMock()
        mock_sb_instance.stop = AsyncMock()
        mock_sb_instance.http_proxy_url = str(client.server.make_url("/"))
        mock_singbox_proxy.return_value = mock_sb_instance

        tester = SingBoxTester()
        proxy = Proxy(config="test_config")

        # We need to patch the TEST_URL to point to our mock server
        with patch("src.configstream.testers.TEST_URL", str(client.server.make_url("/generate_204"))):
            tested_proxy = await tester.test(proxy)

        assert tested_proxy.is_working is True
        assert tested_proxy.latency is not None


@pytest.mark.asyncio
async def test_singbox_tester_failure():
    """Test the SingBoxTester with a failed proxy test."""
    with patch("src.configstream.testers.SingBoxProxy") as mock_singbox_proxy:
        mock_sb_instance = AsyncMock()
        mock_sb_instance.start = AsyncMock(side_effect=Exception("test error"))
        mock_sb_instance.stop = AsyncMock()
        mock_singbox_proxy.return_value = mock_sb_instance

        tester = SingBoxTester()
        proxy = Proxy(config="test_config")
        tested_proxy = await tester.test(proxy)

        assert tested_proxy.is_working is False
        assert "test error" in tested_proxy.security_issues[0]