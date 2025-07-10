"""Mass Config Aggregator Tool.

This module provides a command line tool to collect VPN configuration links from
HTTP sources and Telegram channels, clean and deduplicate them, and output the
results in multiple formats. A Telegram bot mode is also available for on-demand
updates.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Set

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from telethon import TelegramClient, events
from telethon.tl.custom.message import Message


CONFIG_FILE = Path("config.json")
SOURCES_FILE = Path("sources.txt")
CHANNELS_FILE = Path("channels.txt")

PROTOCOL_RE = re.compile(r"(vmess|vless|trojan|ssr?|hysteria2?|tuic)://\S+", re.IGNORECASE)
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=]+$")


@dataclass
class Config:
    telegram_api_id: int
    telegram_api_hash: str
    telegram_bot_token: str
    allowed_user_ids: List[int]
    protocols: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    output_dir: str = "output"
    log_dir: str = "logs"

    @classmethod
    def load(cls, path: Path) -> "Config":
        with path.open("r") as f:
            data = json.load(f)
        return cls(**data)


async def fetch_text(session: ClientSession, url: str) -> str | None:
    """Fetch text content from a URL with retries."""
    for _ in range(3):
        try:
            async with session.get(url, timeout=ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception:
            await asyncio.sleep(1)
    return None


def parse_configs_from_text(text: str) -> Set[str]:
    """Extract all config links from a text block."""
    configs: Set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        match = PROTOCOL_RE.search(line)
        if match:
            configs.add(match.group(0))
            continue
        if BASE64_RE.match(line):
            try:
                decoded = base64.b64decode(line).decode()
                configs.update(PROTOCOL_RE.findall(decoded))
            except Exception:
                continue
    return configs


async def check_and_update_sources(path: Path) -> List[str]:
    """Validate and deduplicate sources list."""
    if not path.exists():
        logging.warning("sources file not found: %s", path)
        return []
    with path.open() as f:
        sources = {line.strip() for line in f if line.strip()}

    valid_sources: List[str] = []
    async with aiohttp.ClientSession() as session:
        for url in sorted(sources):
            text = await fetch_text(session, url)
            if not text:
                logging.info("Removing dead source: %s", url)
                continue
            if not parse_configs_from_text(text):
                logging.info("Removing empty source: %s", url)
                continue
            valid_sources.append(url)

    with path.open("w") as f:
        for url in valid_sources:
            f.write(f"{url}\n")
    logging.info("Valid sources: %d", len(valid_sources))
    return valid_sources


async def fetch_and_parse_configs(sources: Iterable[str]) -> Set[str]:
    """Fetch configs from sources."""
    configs: Set[str] = set()
    async with aiohttp.ClientSession() as session:
        for url in sources:
            text = await fetch_text(session, url)
            if not text:
                logging.warning("Failed to fetch %s", url)
                continue
            configs.update(parse_configs_from_text(text))
    return configs


async def scrape_telegram_configs(channels_path: Path, last_hours: int, cfg: Config) -> Set[str]:
    """Scrape telegram channels for configs."""
    if not channels_path.exists():
        logging.warning("channels file missing: %s", channels_path)
        return set()
    with channels_path.open() as f:
        channels = [line.strip().removeprefix("https://t.me/") for line in f if line.strip()]

    since = datetime.utcnow() - timedelta(hours=last_hours)
    client = TelegramClient("user", cfg.telegram_api_id, cfg.telegram_api_hash)
    await client.start()
    configs: Set[str] = set()
    for channel in channels:
        try:
            async for msg in client.iter_messages(channel, offset_date=since):
                if isinstance(msg, Message) and msg.message:
                    configs.update(parse_configs_from_text(msg.message))
        except Exception as e:
            logging.warning("Failed to scrape %s: %s", channel, e)
    await client.disconnect()
    logging.info("Telegram configs found: %d", len(configs))
    return configs


def deduplicate_and_filter(config_set: Set[str], cfg: Config, protocols: List[str] | None = None) -> List[str]:
    """Apply filters and return sorted configs."""
    final = []
    protocols = protocols or cfg.protocols
    exclude = [re.compile(p) for p in cfg.exclude_patterns]
    for link in sorted(set(c.lower() for c in config_set)):
        if not any(link.startswith(p + "://") for p in protocols):
            continue
        if any(r.search(link) for r in exclude):
            continue
        if "warp://" in link:
            continue
        final.append(link)
    logging.info("Final configs count: %d", len(final))
    return final


def output_files(configs: List[str], out_dir: Path) -> None:
    """Write merged files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    merged_path = out_dir / "merged.txt"
    merged_b64 = out_dir / "merged_base64.txt"
    merged_path.write_text("\n".join(configs))
    merged_b64.write_text(base64.b64encode("\n".join(configs).encode()).decode())
    logging.info("Wrote %s and %s", merged_path, merged_b64)


async def run_pipeline(cfg: Config, protocols: List[str] | None = None) -> Path:
    """Full aggregation pipeline. Returns output directory."""
    sources = await check_and_update_sources(SOURCES_FILE)
    configs = await fetch_and_parse_configs(sources)
    configs |= await scrape_telegram_configs(CHANNELS_FILE, 24, cfg)
    final = deduplicate_and_filter(configs, cfg, protocols)
    out_dir = Path(cfg.output_dir)
    output_files(final, out_dir)
    return out_dir


async def telegram_bot_mode(cfg: Config) -> None:
    """Launch Telegram bot for on-demand updates."""
    bot = TelegramClient("bot", cfg.telegram_api_id, cfg.telegram_api_hash).start(bot_token=cfg.telegram_bot_token)
    last_update = None

    @bot.on(events.NewMessage(pattern="/help"))
    async def help_handler(event: events.NewMessage.Event) -> None:
        if event.sender_id not in cfg.allowed_user_ids:
            return
        await event.respond("/update - run aggregation\n/status - last update time")

    @bot.on(events.NewMessage(pattern="/update"))
    async def update_handler(event: events.NewMessage.Event) -> None:
        nonlocal last_update
        if event.sender_id not in cfg.allowed_user_ids:
            return
        await event.respond("Running update...")
        out_dir = await run_pipeline(cfg)
        for path in out_dir.iterdir():
            await event.respond(file=str(path))
        last_update = datetime.utcnow()

    @bot.on(events.NewMessage(pattern="/status"))
    async def status_handler(event: events.NewMessage.Event) -> None:
        if event.sender_id not in cfg.allowed_user_ids:
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


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Mass VPN Config Aggregator")
    parser.add_argument("--bot", action="store_true", help="run in telegram bot mode")
    parser.add_argument("--protocols", help="comma separated protocols to keep")
    args = parser.parse_args()

    cfg = Config.load(CONFIG_FILE)
    if args.protocols:
        protocols = [p.strip() for p in args.protocols.split(",") if p.strip()]
    else:
        protocols = None

    setup_logging(Path(cfg.log_dir))

    if args.bot:
        asyncio.run(telegram_bot_mode(cfg))
    else:
        asyncio.run(run_pipeline(cfg, protocols))


if __name__ == "__main__":
    main()
