from __future__ import annotations

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

import aiohttp
from massconfigmerger.config import Settings
from massconfigmerger.core.config_processor import ConfigResult
from massconfigmerger.core.utils import (
    get_sort_key,
    is_valid_config,
    choose_proxy,
    fetch_text,
)


def test_get_sort_key_reliability_none():
    """Test get_sort_key with reliability=None."""
    settings = Settings()
    settings.processing.sort_by = "reliability"
    key_func = get_sort_key(settings)
    result = ConfigResult(
        config="vless://test", protocol="VLESS", is_reachable=True, reliability=None
    )
    # Should sort by reachability (False) and reliability (0)
    assert key_func(result) == (False, 0)


@pytest.mark.parametrize(
    "config, expected",
    [
        ("warp://auto", False),
        ("vmess://invalid-json-or-base64", False),
        ("ssr://bm90IGEgdXJs", False),  # "not a url"
        ("ss://YWVzLTEyOC1nY206cGFzc3dvcmQ=@1.1.1.1:8080", True),
        ("ss://YWVzLTEyOC1nY20@1.1.1.1:8080", False), # Missing password in user info
    ],
)
def test_is_valid_config_edge_cases(config: str, expected: bool):
    """Test edge cases for is_valid_config."""
    assert is_valid_config(config) == expected


def test_choose_proxy():
    """Test the choose_proxy function."""
    settings = Settings()
    assert choose_proxy(settings) is None

    settings.network.http_proxy = "http://proxy.com"
    assert choose_proxy(settings) == "http://proxy.com"

    settings.network.socks_proxy = "socks5://proxy.com"
    assert choose_proxy(settings) == "socks5://proxy.com"

    settings.network.http_proxy = None
    assert choose_proxy(settings) == "socks5://proxy.com"


from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_fetch_text_retry_logic():
    """Test that fetch_text retries on failure."""
    mock_session = MagicMock()

    mock_response_success = AsyncMock()
    mock_response_success.status = 200
    mock_response_success.text = AsyncMock(return_value="success")

    mock_cm_success = AsyncMock()
    mock_cm_success.__aenter__.return_value = mock_response_success

    # Fail on the first call, succeed on the second
    mock_session.get.side_effect = [
        aiohttp.ClientError("Connection failed"),
        mock_cm_success,
    ]

    # Use a small delay for testing
    result = await fetch_text(
        mock_session, "http://example.com", retries=2, base_delay=0.01
    )

    assert result == "success"
    assert mock_session.get.call_count == 2