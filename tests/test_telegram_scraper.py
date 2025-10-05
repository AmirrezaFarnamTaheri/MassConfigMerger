from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telethon import errors
from telethon.tl.custom import Message as RealMessage

from massconfigmerger.config import Settings
from massconfigmerger.telegram_scraper import scrape_telegram_configs


@pytest.mark.asyncio
async def test_scrape_telegram_no_credentials():
    """Test that scraping is skipped if credentials are not set."""
    settings = Settings()
    settings.telegram.api_id = None
    configs = await scrape_telegram_configs(settings, Path("channels.txt"), 24)
    assert configs == set()


@pytest.mark.asyncio
async def test_scrape_telegram_no_channels_file(tmp_path: Path):
    """Test that scraping is skipped if the channels file does not exist."""
    settings = Settings(telegram={"api_id": 123, "api_hash": "abc"})
    configs = await scrape_telegram_configs(settings, tmp_path / "nonexistent.txt", 24)
    assert configs == set()


@pytest.mark.asyncio
async def test_scrape_telegram_empty_channels_file(fs):
    """Test that scraping is skipped if the channels file is empty."""
    fs.create_file("channels.txt", contents="")
    settings = Settings(telegram={"api_id": 123, "api_hash": "abc"})
    configs = await scrape_telegram_configs(settings, Path("channels.txt"), 24)
    assert configs == set()


@pytest.mark.asyncio
@patch("massconfigmerger.telegram_scraper.TelegramClient")
@patch("massconfigmerger.telegram_scraper.aiohttp.ClientSession")
async def test_scrape_telegram_success(
    MockClientSession: MagicMock, MockTelegramClient: MagicMock, fs
):
    """Test the successful scraping of configs from Telegram."""
    # Arrange
    fs.create_file(
        "channels.txt",
        contents="t.me/channel1\nchannel2\n",
    )
    settings = Settings(telegram={"api_id": 123, "api_hash": "abc"})

    # Mock TelegramClient
    mock_client = MockTelegramClient.return_value
    mock_client.start = AsyncMock()
    mock_client.is_connected.return_value = True
    mock_client.disconnect = AsyncMock()

    # Mock messages as an async iterator
    async def message_generator(*args, **kwargs):
        mock_msg1 = MagicMock(spec=RealMessage)
        mock_msg1.message = "vless://config1"
        mock_msg1.__class__ = RealMessage
        mock_msg2 = MagicMock(spec=RealMessage)
        mock_msg2.message = "Check this sub: https://example.com/sub"
        mock_msg2.__class__ = RealMessage
        for msg in [mock_msg1, mock_msg2]:
            yield msg

    mock_client.iter_messages.side_effect = [message_generator(), message_generator()]

    # Mock aiohttp session and its context manager
    mock_session = MockClientSession.return_value.__aenter__.return_value
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.text = AsyncMock(return_value="trojan://config2")
    mock_get_cm = AsyncMock()
    mock_get_cm.__aenter__.return_value = mock_resp
    mock_session.get = MagicMock(return_value=mock_get_cm)

    # Act
    configs = await scrape_telegram_configs(settings, Path("channels.txt"), 24)

    # Assert
    mock_client.start.assert_awaited_once()
    assert mock_client.iter_messages.call_count == 2
    assert "vless://config1" in configs
    assert "trojan://config2" in configs
    mock_client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
@patch("massconfigmerger.telegram_scraper.TelegramClient")
async def test_scrape_telegram_rpc_error(MockTelegramClient: MagicMock, fs):
    """Test that RPC errors during scraping are handled gracefully."""
    fs.create_file("channels.txt", contents="badchannel")
    settings = Settings(telegram={"api_id": 123, "api_hash": "abc"})

    mock_client = MockTelegramClient.return_value
    mock_client.start = AsyncMock()
    mock_client.is_connected.return_value = True
    mock_client.disconnect = AsyncMock()
    mock_client.iter_messages.side_effect = errors.RPCError(
        request=None, message="Test Error"
    )

    # Act
    configs = await scrape_telegram_configs(settings, Path("channels.txt"), 24)

    # Assert
    assert configs == set()  # Should be empty as the scrape failed
    mock_client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
@patch("massconfigmerger.telegram_scraper.TelegramClient")
async def test_scrape_telegram_proxy_conversion(MockTelegramClient: MagicMock, fs):
    """Test that HTTP and SOCKS proxies are correctly converted for Telethon."""
    fs.create_file("channels.txt", contents="channel1")
    settings = Settings(telegram={"api_id": 123, "api_hash": "abc"})

    # Mock client methods to avoid TypeErrors
    mock_client = MockTelegramClient.return_value
    mock_client.start = AsyncMock()
    mock_client.is_connected.return_value = True
    mock_client.disconnect = AsyncMock()
    async def empty_iterator(*args, **kwargs):
        if False:
            yield
    mock_client.iter_messages.return_value = empty_iterator()

    # Test SOCKS5 proxy
    settings.network.socks_proxy = "socks5://user:pass@host:1080"
    await scrape_telegram_configs(settings, Path("channels.txt"), 24)
    _, kwargs = MockTelegramClient.call_args
    assert kwargs["proxy"] == ("socks5", "host", 1080, True, "user", "pass")

    # Test HTTP proxy
    settings.network.socks_proxy = None
    settings.network.http_proxy = "http://user:pass@host:8080"
    await scrape_telegram_configs(settings, Path("channels.txt"), 24)
    _, kwargs = MockTelegramClient.call_args
    assert kwargs["proxy"] == ("http", "host", 8080, True, "user", "pass")