import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from configstream.core import Proxy
from configstream.testers import SingBoxTester


@pytest.mark.asyncio
@patch("configstream.testers.SingBoxProxy")
async def test_singbox_tester_timeout(mock_singbox_proxy):
    """Test the SingBoxTester with a timeout."""
    mock_instance = mock_singbox_proxy.return_value
    mock_instance.start = AsyncMock(side_effect=asyncio.TimeoutError)

    tester = SingBoxTester()
    proxy = Proxy(config='direct',
                  protocol="direct",
                  address="localhost",
                  port=80)

    result = await tester.test(proxy)
    assert result.is_working is False


@pytest.mark.asyncio
@patch("configstream.testers.SingBoxProxy")
async def test_singbox_tester_generic_exception(mock_singbox_proxy):
    """Test the SingBoxTester with a generic exception."""
    mock_instance = mock_singbox_proxy.return_value
    mock_instance.start = AsyncMock(
        side_effect=Exception("test error"))

    tester = SingBoxTester()
    proxy = Proxy(config='direct',
                  protocol="direct",
                  address="localhost",
                  port=80)

    result = await tester.test(proxy)
    assert result.is_working is False