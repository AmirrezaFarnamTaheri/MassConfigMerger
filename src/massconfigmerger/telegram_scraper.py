"""Handles scraping configurations from Telegram channels.

This module provides a single entry point, `scrape_telegram_configs`, which
uses the Telethon library to connect to Telegram, iterate through a list of
channels, and parse messages for VPN configuration links. It also handles
fetching and parsing configurations from any subscription links found within
those messages.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Set

import aiohttp
from telethon import TelegramClient, errors
from telethon.tl.custom import Message
from tqdm import tqdm

from .config import Settings
from .core.utils import (
    choose_proxy,
    extract_subscription_urls,
    fetch_text,
    parse_configs_from_text,
)


async def scrape_telegram_configs(
    cfg: Settings, channels_path: Path, last_hours: int
) -> Set[str]:
    """Scrape configurations from Telegram channels."""
    if not all([cfg.telegram.api_id, cfg.telegram.api_hash]):
        logging.info("Telegram credentials not provided; skipping Telegram scrape")
        return set()
    if not channels_path.exists():
        logging.warning("Channels file missing: %s", channels_path)
        return set()

    prefix = "https://t.me/"
    with channels_path.open() as f:
        channels = [
            (
                line.strip()[len(prefix):]
                if line.strip().startswith(prefix)
                else line.strip()
            )
            for line in f
            if line.strip()
        ]

    if not channels:
        logging.info("No channels specified in %s", channels_path)
        return set()

    since = datetime.now(tz=timezone.utc) - timedelta(hours=last_hours)
    proxy = choose_proxy(cfg)

    # Convert aiohttp-style proxy to Telethon proxy if applicable
    telethon_proxy = None
    if proxy:
        # Expecting proxy like "http://host:port" or "socks5://host:port"
        try:
            from urllib.parse import urlparse
            pu = urlparse(proxy)
            if pu.scheme in ("socks5", "socks4"):
                # Telethon expects (proxy_type, addr, port) or with auth
                proxy_type = "socks5" if pu.scheme == "socks5" else "socks4"
                telethon_proxy = (proxy_type, pu.hostname, pu.port, True, pu.username, pu.password)
            elif pu.scheme in ("http", "https"):
                # HTTP proxies can be used with socks via PySocks as HTTP
                telethon_proxy = ("http", pu.hostname, pu.port, True, pu.username, pu.password)
        except Exception as e:
            logging.debug("Failed to adapt proxy for Telethon: %s", e)

    client = TelegramClient(
        cfg.telegram.session_path, cfg.telegram.api_id, cfg.telegram.api_hash, proxy=telethon_proxy
    )
    configs: Set[str] = set()

    try:
        await client.start()
        async with aiohttp.ClientSession(proxy=proxy) as session:
            for channel in tqdm(channels, desc="Scraping Channels", unit="channel"):
                try:
                    async for msg in client.iter_messages(channel, offset_date=since):
                        if isinstance(msg, Message) and msg.message:
                            text = msg.message
                            configs.update(parse_configs_from_text(text))
                            for sub in extract_subscription_urls(text):
                                text2 = await fetch_text(
                                    session,
                                    sub,
                                    cfg.network.request_timeout,
                                    retries=cfg.network.retry_attempts,
                                    base_delay=cfg.network.retry_base_delay,
                                )
                                if text2:
                                    configs.update(parse_configs_from_text(text2))
                except (errors.RPCError, OSError) as e:
                    logging.warning("Error scraping %s: %s", channel, e)
    finally:
        if client.is_connected():
            await client.disconnect()
    return configs
