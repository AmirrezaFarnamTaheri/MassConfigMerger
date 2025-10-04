"""Mass Config Aggregator Tool.

This module provides a command line tool to collect VPN configuration links from
HTTP sources and Telegram channels, clean and deduplicate them, and output the
results in multiple formats.  A Telegram bot mode is also available for
on-demand updates.  The script is intended for local, one-shot execution and can
be scheduled with cron or Task Scheduler if desired.
"""

from __future__ import annotations

import asyncio
import argparse
import logging
import re
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set, cast

import aiohttp
from telethon import TelegramClient, events, errors
from telethon.tl.custom.message import Message
from tqdm import tqdm

from . import output_writer
from .config import Settings, load_config
from .constants import SOURCES_FILE

CONFIG_FILE = Path("config.yaml")
CHANNELS_FILE = Path("channels.txt")
from .core.config_processor import ConfigProcessor
from .core.output_generator import OutputGenerator
from .core.source_manager import SourceManager
from .core.utils import (
    choose_proxy,
    fetch_text,
    parse_configs_from_text,
    print_public_source_warning,
)

# Match full config links for supported protocols
HTTP_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def extract_subscription_urls(text: str) -> Set[str]:
    """Return all HTTP(S) URLs in the text block."""
    urls: Set[str] = set()
    for match in HTTP_RE.findall(text):
        urls.add(match.rstrip(")].,!?:;"))
    return urls


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
            (line.strip()[len(prefix) :] if line.strip().startswith(prefix) else line.strip())
            for line in f
            if line.strip()
        ]

    if not channels:
        logging.info("No channels specified in %s", channels_path)
        return set()

    since = datetime.utcnow() - timedelta(hours=last_hours)
    client = TelegramClient(cfg.telegram.session_path, cfg.telegram.api_id, cfg.telegram.api_hash)
    configs: Set[str] = set()

    try:
        await client.start()
        proxy = choose_proxy(cfg)
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
                                    proxy=proxy,
                                )
                                if text2:
                                    configs.update(parse_configs_from_text(text2))
                except (errors.RPCError, OSError) as e:
                    logging.warning("Error scraping %s: %s", channel, e)
    finally:
        if client.is_connected():
            await client.disconnect()

    logging.info("Found %d configs from Telegram", len(configs))
    return configs


async def run_pipeline(
    cfg: Settings,
    protocols: List[str] | None = None,
    sources_file: Path = SOURCES_FILE,
    channels_file: Path = CHANNELS_FILE,
    last_hours: int = 24,
    *,
    failure_threshold: int = 3,
    prune: bool = True,
) -> tuple[Path, list[Path]]:
    """Run the aggregation pipeline and return output directory and files."""
    source_manager = SourceManager(cfg)
    config_processor = ConfigProcessor(cfg)
    output_generator = OutputGenerator(cfg)

    try:
        # Fetch sources and configs
        available_sources = await source_manager.check_and_update_sources(
            sources_file, max_failures=failure_threshold, prune=prune
        )
        configs = await source_manager.fetch_sources(available_sources)

        # Scrape Telegram configs
        telegram_configs = await scrape_telegram_configs(
            cfg, channels_file, last_hours
        )
        configs.update(telegram_configs)

        # Filter and process configs
        filtered_configs = config_processor.filter_configs(configs, protocols)

        # Write output files
        output_dir = Path(cfg.output.output_dir)
        files = output_generator.write_outputs(filtered_configs, output_dir)

        logging.info("Aggregation complete. Found %d configs.", len(filtered_configs))
        return output_dir, files

    finally:
        await source_manager.close_session()


async def telegram_bot_mode(
    cfg: Settings,
    sources_file: Path = SOURCES_FILE,
    channels_file: Path = CHANNELS_FILE,
    last_hours: int = 24,
) -> None:
    """Launch Telegram bot for on-demand updates."""
    if not all(
        [
            cfg.telegram.api_id,
            cfg.telegram.api_hash,
            cfg.telegram.bot_token,
            cfg.telegram.allowed_user_ids,
        ]
    ):
        logging.info("Telegram credentials not provided; skipping bot mode")
        return

    bot = cast(
        TelegramClient,
        TelegramClient(
            cfg.telegram.session_path, cfg.telegram.api_id, cfg.telegram.api_hash
        ).start(bot_token=cfg.telegram.bot_token),
    )
    last_update = None

    @bot.on(events.NewMessage(pattern="/help"))
    async def help_handler(event: events.NewMessage.Event) -> None:
        if event.sender_id not in cfg.telegram.allowed_user_ids:
            return
        await event.respond("/update - run aggregation\n/status - last update time")

    @bot.on(events.NewMessage(pattern="/update"))
    async def update_handler(event: events.NewMessage.Event) -> None:
        nonlocal last_update
        if event.sender_id not in cfg.telegram.allowed_user_ids:
            return
        await event.respond("Running update...")
        _out_dir, files = await run_pipeline(
            cfg,
            sources_file=sources_file,
            channels_file=channels_file,
            last_hours=last_hours,
        )

        for path in files:
            await event.respond(file=str(path))
        last_update = datetime.utcnow()

    @bot.on(events.NewMessage(pattern="/status"))
    async def status_handler(event: events.NewMessage.Event) -> None:
        if event.sender_id not in cfg.telegram.allowed_user_ids:
            return
        msg = "Never" if not last_update else last_update.isoformat()
        await event.respond(f"Last update: {msg}")

    logging.info("Bot running. Press Ctrl+C to exit.")
    await bot.run_until_disconnected()


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{datetime.utcnow().date()}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


# This file is not intended to be run directly anymore.
# The main entry point is now cli.py.