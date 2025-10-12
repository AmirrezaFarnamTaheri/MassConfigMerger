from __future__ import annotations
import base64
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import socket

import pytest
import aiohttp

from configstream.core.utils import (
    parse_configs_from_text,
    get_sort_key,
    choose_proxy,
    fetch_text,
    is_safe_url,
)
from configstream.config import Settings
from configstream.core.config_processor import ConfigResult
from configstream.exceptions import ConfigError, NetworkError


def test_parse_configs_from_text_oversized_b64():
    """Test that oversized base64 lines are skipped."""
    # Create a base64 string that is longer than the max size
    long_string = "a" * 5000
    b64_string = base64.urlsafe_b64encode(long_string.encode()).decode()
    text = f"some text\n{b64_string}\nmore text"

    with patch("configstream.core.utils.MAX_DECODE_SIZE", 4000):
        configs = parse_configs_from_text(text)
        assert len(configs) == 0


def test_parse_configs_from_text_invalid_b64():
    """Test that invalid base64 lines are skipped."""
    text = "some text\ninvalid-base64-string\nmore text"
    configs = parse_configs_from_text(text)
    assert len(configs) == 0


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


def test_choose_proxy():
    """Test the choose_proxy function."""
    settings = Settings()
    assert choose_proxy(settings) is None

    settings.network.http_proxy = "http://proxy.com"
    assert choose_proxy(settings) == "http://proxy.com"

    settings.network.http_proxy = None
    settings.network.socks_proxy = "socks5://proxy.com"
    assert choose_proxy(settings) == "socks5://proxy.com"

    settings.network.http_proxy = None
    assert choose_proxy(settings) == "socks5://proxy.com"


@pytest.mark.parametrize(
    "url, expected",
    [
        ("http://example.com", True),
        ("https://google.com/search?q=test", True),
        ("ftp://example.com", False),
        ("file:///etc/passwd", False),
        ("http://localhost/admin", False),
        ("https://127.0.0.1:8080", False),
        ("http://169.254.169.254/latest/meta-data", False),
        ("http://metadata.google.internal", False),
        ("http://[::1]:8080/", False),
    ]
)
def test_is_safe_url(url, expected):
    from configstream.core.utils import is_safe_url
    assert is_safe_url(url) == expected


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
    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_get_loop.return_value.getaddrinfo = AsyncMock(return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 0))
        ])
        result = await fetch_text(
            mock_session, "http://example.com", timeout=10, retries=2, base_delay=0.01, jitter=0.1
        )

    assert result == "success"
    assert mock_session.get.call_count == 2


@pytest.fixture
def mock_session():
    """Fixture for a mocked aiohttp ClientSession."""
    session = MagicMock(spec=aiohttp.ClientSession)

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text.return_value = "Success"

    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = mock_response
    session.get.return_value = async_cm

    return session


@pytest.mark.asyncio
@patch("asyncio.get_running_loop")
async def test_fetch_text_ssrf_safe_ip(mock_get_loop, mock_session):
    """Test fetch_text with a URL that resolves to a safe IP."""
    mock_get_loop.return_value.getaddrinfo = AsyncMock(return_value=[
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 0))
    ])

    url = "http://safe.example.com"
    await fetch_text(mock_session, url)

    mock_session.get.assert_called_once()
    call_args, call_kwargs = mock_session.get.call_args
    assert call_args[0] == "http://8.8.8.8:80/"
    assert call_kwargs["headers"] == {"Host": "safe.example.com"}


@pytest.mark.asyncio
async def test_fetch_text_ssrf_blocked_host(mock_session):
    """Test that fetch_text blocks requests to localhost."""
    url = "http://localhost/secret"
    with pytest.raises(NetworkError, match="Blocked or invalid hostname"):
        await fetch_text(mock_session, url)


@pytest.mark.asyncio
@patch("asyncio.get_running_loop")
async def test_fetch_text_ssrf_private_ip(mock_get_loop, mock_session):
    """Test that fetch_text blocks URLs resolving to private IPs."""
    mock_get_loop.return_value.getaddrinfo = AsyncMock(return_value=[
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.1', 0))
    ])

    url = "http://private.example.com"
    with pytest.raises(NetworkError, match="No safe, public IP address found"):
        await fetch_text(mock_session, url)


@pytest.mark.asyncio
@patch("asyncio.get_running_loop")
async def test_fetch_text_ssrf_dns_failure(mock_get_loop, mock_session):
    """Test that fetch_text handles DNS resolution failures."""
    mock_get_loop.return_value.getaddrinfo = AsyncMock(
        side_effect=socket.gaierror)

    url = "http://nonexistent.domain.xyz"
    with pytest.raises(NetworkError, match="DNS resolution failed"):
        await fetch_text(mock_session, url)


@pytest.mark.asyncio
async def test_fetch_text_invalid_url_scheme(mock_session):
    """Test that fetch_text rejects invalid URL schemes."""
    url = "ftp://example.com/resource"
    with pytest.raises(NetworkError, match="Invalid URL scheme"):
        await fetch_text(mock_session, url)


def test_parse_configs_from_text_oversized_base64_final():
    """Test that oversized base64 lines are skipped."""
    # This line is valid base64 but exceeds the default MAX_DECODE_SIZE
    long_line = "a" * 8192
    # The function should not raise an error and simply return an empty set
    configs = parse_configs_from_text(long_line)
    assert configs == set()


def test_choose_proxy_with_both_set():
    """Test that choose_proxy raises ConfigError if both proxies are set."""
    settings = Settings()
    settings.network.http_proxy = "http://proxy.com"
    settings.network.socks_proxy = "socks5://proxy.com"
    with pytest.raises(ConfigError):
        choose_proxy(settings)


@pytest.mark.asyncio
async def test_fetch_text_invalid_scheme():
    """Test fetch_text with an invalid URL scheme."""
    mock_session = MagicMock()
    with pytest.raises(NetworkError, match="Invalid URL scheme"):
        await fetch_text(mock_session, "ftp://example.com")


def test_is_safe_url_invalid_url_type():
    """Test is_safe_url with a type that causes a ValueError on urlparse."""
    # urlparse can raise ValueError for certain malformed bytes-like objects
    # or other non-string inputs.
    assert not is_safe_url(12345)
    assert not is_safe_url(None)