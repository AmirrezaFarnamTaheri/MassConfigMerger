from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from telethon import errors

from massconfigmerger.config import Settings
from massconfigmerger.telegram_scraper import scrape_telegram_configs


class FakeMessage:
    """A fake class to mimic telethon's Message for testing."""
    def __init__(self, text: str):
        self.message = text

@pytest.mark.asyncio
async def test_scrape_with_subscription_link():
    """Test that subscription links found in messages are fetched and parsed."""
    settings = Settings()
    settings.telegram.api_id = 123
    settings.telegram.api_hash = "abc"

    with patch("massconfigmerger.telegram_scraper.datetime") as mock_datetime, \
         patch("massconfigmerger.telegram_scraper.TelegramClient") as MockTelegramClient, \
         patch("pathlib.Path.open", mock_open(read_data="channel1")), \
         patch("massconfigmerger.telegram_scraper.choose_proxy", return_value=None), \
         patch("massconfigmerger.telegram_scraper.aiohttp.ClientSession"), \
         patch("massconfigmerger.telegram_scraper.tqdm", new=lambda x, **kwargs: x), \
         patch("massconfigmerger.telegram_scraper.Message", new=FakeMessage), \
         patch("massconfigmerger.telegram_scraper.fetch_text", new_callable=AsyncMock) as mock_fetch_text:

        mock_datetime.utcnow.return_value = datetime(2023, 1, 2)

        mock_client = MockTelegramClient.return_value
        mock_client.start = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.is_connected.return_value = True

        msg = FakeMessage("Check out this list: https://example.com/sub.txt")

        async def message_iterator():
            yield msg

        mock_client.iter_messages.return_value = message_iterator()
        mock_fetch_text.return_value = "vless://sub-config-1"

        configs = await scrape_telegram_configs(settings, Path("channels.txt"), 24)

        assert "vless://sub-config-1" in configs
        mock_fetch_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_with_rpc_error():
    """Test that RPC errors during scraping are handled gracefully."""
    settings = Settings()
    settings.telegram.api_id = 123
    settings.telegram.api_hash = "abc"

    with patch("massconfigmerger.telegram_scraper.datetime") as mock_datetime, \
         patch("massconfigmerger.telegram_scraper.TelegramClient") as MockTelegramClient, \
         patch("pathlib.Path.open", mock_open(read_data="channel1")), \
         patch("massconfigmerger.telegram_scraper.choose_proxy", return_value=None), \
         patch("massconfigmerger.telegram_scraper.aiohttp.ClientSession"), \
         patch("massconfigmerger.telegram_scraper.tqdm", new=lambda x, **kwargs: x), \
         patch("massconfigmerger.telegram_scraper.Message", new=FakeMessage):

        mock_datetime.utcnow.return_value = datetime(2023, 1, 2)

        mock_client = MockTelegramClient.return_value
        mock_client.start = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.is_connected.return_value = True

        # Correctly instantiate the RPCError with keyword arguments
        mock_client.iter_messages.side_effect = errors.RPCError(request=None, message="Test Error", code=400)

        configs = await scrape_telegram_configs(settings, Path("channels.txt"), 24)

        assert configs == set()
        mock_client.disconnect.assert_awaited_once()