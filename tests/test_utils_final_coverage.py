import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import base64

from configstream.core.utils import (
    parse_configs_from_text,
    choose_proxy,
    fetch_text,
    is_safe_url,
)
from configstream.config import Settings
from configstream.exceptions import ConfigError, NetworkError


def test_parse_configs_from_text_oversized_base64():
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
