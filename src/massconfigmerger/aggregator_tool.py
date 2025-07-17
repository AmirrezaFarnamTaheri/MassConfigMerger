"""Mass Config Aggregator Tool.

This module provides a command line tool to collect VPN configuration links from
HTTP sources and Telegram channels, clean and deduplicate them, and output the
results in multiple formats.  A Telegram bot mode is also available for
on-demand updates.  The script is intended for local, one-shot execution and can
be scheduled with cron or Task Scheduler if desired.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import uuid
import json
import logging
import random  # noqa: F401 - used in tests for monkeypatching
import re
import argparse
from datetime import datetime, timedelta
import time
import sys
import os
from pathlib import Path
from typing import Iterable, List, Set, Dict, Tuple, cast, Any
from .clash_utils import config_to_clash_proxy, build_clash_config

import io
from contextlib import redirect_stdout



import aiohttp
from aiohttp import ClientSession
from .source_fetcher import fetch_text
from tqdm import tqdm
from telethon import TelegramClient, events, errors  # type: ignore
from telethon.tl.custom.message import Message  # type: ignore
from . import vpn_merger
from . import output_writer

from .constants import SOURCES_FILE
from .utils import (
    is_valid_config,
    parse_configs_from_text,
    print_public_source_warning,
    choose_proxy,
)
from .result_processor import EnhancedConfigProcessor

from .config import Settings, load_config

CONFIG_FILE = Path("config.yaml")
CHANNELS_FILE = Path("channels.txt")

# Match full config links for supported protocols
# (regex patterns defined in constants and used via utils)
HTTP_RE = re.compile(r"https?://\S+", re.IGNORECASE)

# Safety limit for base64 decoding to avoid huge payloads (imported from utils)

def extract_subscription_urls(text: str) -> Set[str]:
    """Return all HTTP(S) URLs in the text block.

    Trailing punctuation such as ``)``, ``]``, ``,``, ``.``, ``!``, ``?``, or ``;``
    is stripped from the matched URLs.
    """

    urls: Set[str] = set()
    for match in HTTP_RE.findall(text):
        urls.add(match.rstrip(")].,!?:;"))
    return urls


class Aggregator:
    """Aggregate VPN configs while tracking summary statistics."""

    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg
        self.stats: Dict[str, int] = {
            "valid_sources": 0,
            "fetched_configs": 0,
            "written_configs": 0,
        }

    async def check_and_update_sources(
        self,
        path: Path,
        concurrent_limit: int = 20,
        request_timeout: int = 10,
        *,
        retries: int = 3,
        base_delay: float = 1.0,
        failures_path: Path | None = None,
        max_failures: int = 3,
        prune: bool = True,
        disabled_path: Path | None = None,
        proxy: str | None = None,
        session: ClientSession | None = None,
    ) -> List[str]:
        if not path.exists():
            logging.warning("sources file not found: %s", path)
            return []

        if failures_path is None:
            failures_path = path.with_suffix(".failures.json")

        try:
            failures = json.loads(failures_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning("Failed to load failures file: %s", exc)
            failures = {}

        with path.open() as f:
            seen = set()
            sources: List[str] = []
            for line in f:
                url = line.strip()
                if not url:
                    continue
                if url not in seen:
                    seen.add(url)
                    sources.append(url)

        valid_sources: List[str] = []
        removed: List[str] = []
        semaphore = asyncio.Semaphore(concurrent_limit)

        async def check(sess: ClientSession, url: str) -> tuple[str, bool]:
            async with semaphore:
                text = await fetch_text(
                    sess,
                    url,
                    request_timeout,
                    retries=retries,
                    base_delay=base_delay,
                    proxy=proxy,
                )
            if not text or not parse_configs_from_text(text):
                return url, False
            return url, True

        async def run_checks(sess: ClientSession) -> None:
            tasks = [asyncio.create_task(check(sess, u)) for u in sources]
            for task in asyncio.as_completed(tasks):
                url, ok = await task
                if ok:
                    failures.pop(url, None)
                    valid_sources.append(url)
                else:
                    failures[url] = failures.get(url, 0) + 1
                    if prune and failures[url] >= max_failures:
                        removed.append(url)

        if session is None:
            connector = aiohttp.TCPConnector(limit=concurrent_limit)
            if proxy:
                session_cm = aiohttp.ClientSession(connector=connector, proxy=proxy)
            else:
                session_cm = aiohttp.ClientSession(connector=connector)
            async with session_cm as sess:
                await run_checks(sess)
        else:
            await run_checks(session)

        remaining = [u for u in sources if u not in removed]
        with path.open("w") as f:
            for url in remaining:
                f.write(f"{url}\n")

        if disabled_path and removed:
            timestamp = datetime.utcnow().isoformat()
            with disabled_path.open("a") as f:
                for url in removed:
                    f.write(f"{timestamp} {url}\n")
        for url in removed:
            failures.pop(url, None)

        failures_path.write_text(json.dumps(failures, indent=2))

        logging.info("Valid sources: %d", len(valid_sources))
        return valid_sources

    async def fetch_and_parse_configs(
        self,
        sources: Iterable[str],
        concurrent_limit: int = 20,
        request_timeout: int = 10,
        *,
        retries: int = 3,
        base_delay: float = 1.0,
        proxy: str | None = None,
        session: ClientSession | None = None,
    ) -> Set[str]:
        configs: Set[str] = set()

        source_list = list(sources)
        if self.cfg.shuffle_sources:
            random.shuffle(source_list)
        semaphore = asyncio.Semaphore(concurrent_limit)

        async def fetch_one(session: ClientSession, url: str) -> Set[str]:
            async with semaphore:
                text = await fetch_text(
                    session,
                    url,
                    request_timeout,
                    retries=retries,
                    base_delay=base_delay,
                    proxy=proxy,
                )
            if not text:
                logging.warning("Failed to fetch %s", url)
                return set()
            return parse_configs_from_text(text)

        async def run_fetch(sess: ClientSession) -> None:
            tasks = [asyncio.create_task(fetch_one(sess, u)) for u in source_list]
            for task in asyncio.as_completed(tasks):
                configs.update(await task)
                if self.cfg.enable_url_testing:
                    progress.update(1)

        progress = tqdm(total=len(source_list), desc="Sources", unit="src", leave=False)
        try:
            if session is None:
                connector = aiohttp.TCPConnector(limit=concurrent_limit)
                if proxy:
                    session_cm = aiohttp.ClientSession(connector=connector, proxy=proxy)
                else:
                    session_cm = aiohttp.ClientSession(connector=connector)
                async with session_cm as sess:
                    await run_fetch(sess)
            else:
                await run_fetch(session)
        finally:
            progress.close()

        return configs

    async def scrape_telegram_configs(
        self, channels_path: Path, last_hours: int
    ) -> Set[str]:
        cfg = self.cfg
        if cfg.telegram_api_id is None or cfg.telegram_api_hash is None:
            logging.info("Telegram credentials not provided; skipping Telegram scrape")
            return set()
        if not channels_path.exists():
            logging.warning("channels file missing: %s", channels_path)
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

        since = datetime.utcnow() - timedelta(hours=last_hours)
        client = TelegramClient(
            cfg.session_path, cfg.telegram_api_id, cfg.telegram_api_hash
        )
        progress = tqdm(total=len(channels), desc="Channels", unit="chan", leave=False)
        configs: Set[str] = set()

        try:
            await client.start()
            async with aiohttp.ClientSession(proxy=choose_proxy(cfg)) as session:
                for channel in channels:
                    count_before = len(configs)
                    success = False
                    for _ in range(2):
                        try:
                            async for msg in client.iter_messages(
                                channel, offset_date=since
                            ):
                                if isinstance(msg, Message) and msg.message:
                                    text = msg.message
                                    configs.update(parse_configs_from_text(text))
                                    for sub in extract_subscription_urls(text):
                                        text2 = await fetch_text(
                                            session,
                                            sub,
                                            cfg.request_timeout,
                                            retries=cfg.retry_attempts,
                                            base_delay=cfg.retry_base_delay,
                                            proxy=choose_proxy(cfg),
                                        )
                                        if text2:
                                            configs.update(parse_configs_from_text(text2))
                            success = True
                            break
                        except (errors.RPCError, OSError) as e:
                            logging.warning("Error scraping %s: %s", channel, e)
                            try:
                                await client.disconnect()
                                await client.connect()
                            except (errors.RPCError, OSError) as rexc:
                                logging.warning("Reconnect failed: %s", rexc)
                                break
                    if not success:
                        logging.warning("Skipping %s due to repeated errors", channel)
                        progress.update(1)
                        continue
                    logging.info(
                        "Channel %s -> %d new configs",
                        channel,
                        len(configs) - count_before,
                    )
                    progress.update(1)
            await client.disconnect()
        except (errors.RPCError, OSError, aiohttp.ClientError) as e:
            logging.warning("Telegram connection failed: %s", e)
            try:
                await client.disconnect()
            except (errors.RPCError, OSError):
                pass
            return set()
        finally:
            progress.close()

        logging.info("Telegram configs found: %d", len(configs))
        return configs

    @staticmethod
    def output_files(
        configs: List[str], out_dir: Path, cfg: Settings
    ) -> List[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        written: List[Path] = []

        def _atomic_write(path: Path, data: str) -> None:
            tmp = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
            try:
                tmp.write_text(data, encoding="utf-8")
                tmp.replace(path)
            finally:
                if tmp.exists():
                    tmp.unlink(missing_ok=True)

        merged_path = out_dir / "vpn_subscription_raw.txt"
        text = "\n".join(configs)
        _atomic_write(merged_path, text)
        written.append(merged_path)

        if cfg.write_base64:
            merged_b64 = out_dir / "vpn_subscription_base64.txt"
            b64_content = base64.b64encode(text.encode()).decode()
            _atomic_write(merged_b64, b64_content)
            written.append(merged_b64)

            try:
                base64.b64decode(b64_content).decode()
            except (binascii.Error, UnicodeDecodeError) as exc:
                logging.warning("Base64 validation failed: %s", exc)

        if cfg.write_singbox:
            outbounds = []
            for idx, link in enumerate(configs):
                proto = link.split("://", 1)[0].lower()
                outbounds.append({"type": proto, "tag": f"node-{idx}", "raw": link})
            merged_singbox = out_dir / "vpn_singbox.json"
            _atomic_write(
                merged_singbox,
                json.dumps({"outbounds": outbounds}, indent=2, ensure_ascii=False),
            )
            written.append(merged_singbox)

        proxies: List[Dict[str, Any]] = []
        need_proxies = (
            cfg.write_clash or cfg.surge_file or cfg.qx_file or cfg.xyz_file
        )
        if need_proxies:
            for idx, link in enumerate(configs):
                proxy = config_to_clash_proxy(link, idx)
                if proxy:
                    proxies.append(proxy)

        if cfg.write_clash and proxies:
            clash_yaml = build_clash_config(proxies)
            clash_file = out_dir / "clash.yaml"
            _atomic_write(clash_file, clash_yaml)
            written.append(clash_file)

        if cfg.surge_file and proxies:
            from .advanced_converters import generate_surge_conf

            surge_content = generate_surge_conf(proxies)
            surge_path = Path(cfg.surge_file)
            if not surge_path.is_absolute():
                surge_path = out_dir / surge_path
            _atomic_write(surge_path, surge_content)
            written.append(surge_path)

        if cfg.qx_file and proxies:
            from .advanced_converters import generate_qx_conf

            qx_content = generate_qx_conf(proxies)
            qx_path = Path(cfg.qx_file)
            if not qx_path.is_absolute():
                qx_path = out_dir / qx_path
            _atomic_write(qx_path, qx_content)
            written.append(qx_path)

        if cfg.xyz_file and proxies:
            xyz_lines = [
                f"{p.get('name')},{p.get('server')},{p.get('port')}" for p in proxies
            ]
            xyz_path = Path(cfg.xyz_file)
            if not xyz_path.is_absolute():
                xyz_path = out_dir / xyz_path
            _atomic_write(xyz_path, "\n".join(xyz_lines))
            written.append(xyz_path)

        logging.info(
            "Wrote %s%s%s%s%s%s%s",
            merged_path,
            ", vpn_subscription_base64.txt" if cfg.write_base64 else "",
            ", vpn_singbox.json" if cfg.write_singbox else "",
            ", clash.yaml" if cfg.write_clash and proxies else "",
            f", {Path(cfg.surge_file).name}" if cfg.surge_file else "",
            f", {Path(cfg.qx_file).name}" if cfg.qx_file else "",
            f", {Path(cfg.xyz_file).name}" if cfg.xyz_file else "",
        )

        return written

    async def run(
        self,
        protocols: List[str] | None = None,
        sources_file: Path = SOURCES_FILE,
        channels_file: Path = CHANNELS_FILE,
        last_hours: int = 24,
        *,
        failure_threshold: int = 3,
        prune: bool = True,
    ) -> Tuple[Path, List[Path]]:
        cfg = self.cfg
        out_dir = Path(cfg.output_dir)
        start = time.time()

        proxy = choose_proxy(cfg)
        connector = aiohttp.TCPConnector(limit=cfg.concurrent_limit)
        session = aiohttp.ClientSession(connector=connector, proxy=proxy)

        configs: Set[str] = set()
        try:
            configs = await self._load_sources(
                sources_file,
                failure_threshold,
                prune,
                proxy=proxy,
                session=session,
            )
            configs |= await self._scrape_telegram(channels_file, last_hours)
            self.stats["fetched_configs"] = len(configs)
            logging.info("Fetched configs count: %d", self.stats["fetched_configs"])
        except KeyboardInterrupt:
            logging.warning("Interrupted. Writing partial results...")
        finally:
            files = self._write_outputs(configs, protocols, out_dir)
            await session.close()
            elapsed = time.time() - start
            summary = (
                f"Sources checked: {self.stats['valid_sources']} | "
                f"Configs fetched: {self.stats['fetched_configs']} | "
                f"Unique configs: {self.stats['written_configs']} | "
                f"Elapsed: {elapsed:.1f}s"
            )
            print(summary)
            logging.info(summary)
        return out_dir, files

    async def _load_sources(
        self,
        sources_file: Path,
        failure_threshold: int,
        prune: bool,
        *,
        proxy: str | None = None,
        session: ClientSession | None = None,
    ) -> Set[str]:
        cfg = self.cfg
        sources = await self.check_and_update_sources(
            sources_file,
            cfg.concurrent_limit,
            cfg.request_timeout,
            retries=cfg.retry_attempts,
            base_delay=cfg.retry_base_delay,
            failures_path=sources_file.with_suffix(".failures.json"),
            max_failures=failure_threshold,
            prune=prune,
            disabled_path=(
                sources_file.with_name("sources_disabled.txt") if prune else None
            ),
            proxy=proxy,
            session=session,
        )
        self.stats["valid_sources"] = len(sources)
        configs = await self.fetch_and_parse_configs(
            sources,
            cfg.concurrent_limit,
            cfg.request_timeout,
            retries=cfg.retry_attempts,
            base_delay=cfg.retry_base_delay,
            proxy=proxy,
            session=session,
        )
        return configs

    async def _scrape_telegram(
        self, channels_file: Path, last_hours: int
    ) -> Set[str]:
        return await self.scrape_telegram_configs(channels_file, last_hours)

    def _write_outputs(
        self,
        configs: Set[str],
        protocols: List[str] | None,
        out_dir: Path,
    ) -> List[Path]:
        cfg = self.cfg
        final = deduplicate_and_filter(configs, cfg, protocols)
        self.stats["written_configs"] = len(final)
        logging.info("Final configs count: %d", self.stats["written_configs"])
        return Aggregator.output_files(final, out_dir, cfg)

def output_files(configs: List[str], out_dir: Path, cfg: Settings) -> List[Path]:
    """Convenience wrapper around Aggregator.output_files."""
    return Aggregator.output_files(configs, out_dir, cfg)











def deduplicate_and_filter(
    config_set: Set[str], cfg: Settings, protocols: List[str] | None = None
) -> List[str]:
    """Apply filters and return sorted configs.

    If ``protocols`` resolves to an empty list after considering ``cfg.protocols``,
    no protocol filtering is applied and all links are accepted (subject to the
    other filters).
    """
    final = []
    # ``protocols`` overrides ``cfg.protocols`` when provided, even if empty
    if protocols is None:
        protocols = cfg.protocols
    if protocols:
        protocols = [p.lower() for p in protocols]
    exclude = [re.compile(p, re.IGNORECASE) for p in cfg.exclude_patterns]
    include = [re.compile(p, re.IGNORECASE) for p in cfg.include_patterns]
    processor = EnhancedConfigProcessor()
    seen: Set[str] = set()
    for link in sorted(c.strip() for c in config_set):
        l_lower = link.lower()
        link_hash = processor.create_semantic_hash(link)
        if link_hash in seen:
            continue
        seen.add(link_hash)
        if protocols and not any(l_lower.startswith(p + "://") for p in protocols):
            continue
        if any(r.search(l_lower) for r in exclude):
            continue
        if include and not any(r.search(l_lower) for r in include):
            continue
        if not is_valid_config(link):

            continue
        final.append(link)
    logging.info("Final configs count: %d", len(final))
    return final




async def run_pipeline(
    cfg: Settings,
    protocols: List[str] | None = None,
    sources_file: Path = SOURCES_FILE,
    channels_file: Path = CHANNELS_FILE,
    last_hours: int = 24,
    *,
    failure_threshold: int = 3,
    prune: bool = True,
) -> Tuple[Path, List[Path]]:
    """Run the aggregation pipeline and return output directory and files."""
    aggregator = Aggregator(cfg)
    return await aggregator.run(
        protocols,
        sources_file,
        channels_file,
        last_hours,
        failure_threshold=failure_threshold,
        prune=prune,
    )


async def telegram_bot_mode(
    cfg: Settings,
    sources_file: Path = SOURCES_FILE,
    channels_file: Path = CHANNELS_FILE,
    last_hours: int = 24,
) -> None:
    """Launch Telegram bot for on-demand updates."""
    if not all(
        [
            cfg.telegram_api_id,
            cfg.telegram_api_hash,
            cfg.telegram_bot_token,
            cfg.allowed_user_ids,
        ]
    ):
        logging.info("Telegram credentials not provided; skipping bot mode")
        return

    bot = cast(
        TelegramClient,
        TelegramClient(
            cfg.session_path, cfg.telegram_api_id, cfg.telegram_api_hash
        ).start(bot_token=cfg.telegram_bot_token),
    )
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
        aggregator = Aggregator(cfg)
        out_dir, files = await aggregator.run(
            None,
            sources_file,
            channels_file,
            last_hours,
        )

        for path in files:
            await event.respond(file=str(path))  # type: ignore[call-arg]
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


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    """Return an argument parser configured for the aggregator tool."""
    if parser is None:
        parser = argparse.ArgumentParser(
            description=(
                "Mass VPN Config Aggregator. Telegram credentials are only required "
                "when scraping Telegram or running bot mode"
            )
        )
    parser.add_argument("--bot", action="store_true", help="run in telegram bot mode")
    parser.add_argument("--protocols", help="comma separated protocols to keep")
    parser.add_argument(
        "--include-pattern",
        action="append",
        help="regular expression configs must match (can be repeated)",
    )
    parser.add_argument(
        "--exclude-pattern",
        action="append",
        help="regular expression to skip configs (can be repeated)",
    )
    parser.add_argument(
        "--config", default=str(CONFIG_FILE), help="path to config.yaml"
    )
    parser.add_argument(
        "--sources", default=str(SOURCES_FILE), help="path to sources.txt"
    )
    parser.add_argument(
        "--channels", default=str(CHANNELS_FILE), help="path to channels.txt"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="how many hours of Telegram history to scan (default %(default)s)",
    )
    parser.add_argument("--output-dir", help="override output directory from config")
    parser.add_argument(
        "--concurrent-limit",
        type=int,
        help="maximum simultaneous HTTP requests",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        help="HTTP request timeout in seconds",
    )
    parser.add_argument(
        "--failure-threshold",
        type=int,
        default=3,
        help="consecutive failures before pruning a source",
    )
    parser.add_argument(
        "--no-prune", action="store_true", help="do not remove failing sources"
    )
    parser.add_argument(
        "--no-base64", action="store_true", help="skip vpn_subscription_base64.txt"
    )
    parser.add_argument(
        "--no-singbox", action="store_true", help="skip vpn_singbox.json"
    )
    parser.add_argument("--no-clash", action="store_true", help="skip clash.yaml")
    parser.add_argument(
        "--write-html",
        action="store_true",
        help="enable vpn_report.html when used with --with-merger",
    )
    parser.add_argument(
        "--shuffle-sources",
        action="store_true",
        help="process sources in random order",
    )
    parser.add_argument(
        "--output-surge",
        metavar="FILE",
        type=str,
        default=None,
        help="write Surge formatted proxy list to FILE",
    )
    parser.add_argument(
        "--output-qx",
        metavar="FILE",
        type=str,
        default=None,
        help="write Quantumult X formatted proxy list to FILE",
    )
    parser.add_argument(
        "--output-xyz",
        metavar="FILE",
        type=str,
        default=None,
        help="write XYZ formatted proxy list to FILE",
    )
    parser.add_argument(
        "--with-merger",
        action="store_true",
        help="run vpn_merger on the aggregated results using the resume feature",
    )
    parser.add_argument(
        "--upload-gist",
        action="store_true",
        help="upload generated files to a GitHub Gist",
    )

    return parser


def main(args: argparse.Namespace | None = None) -> None:
    print_public_source_warning()
    if args is None:
        args = build_parser().parse_args()

    try:
        cfg = load_config(Path(args.config))
    except ValueError:
        print("Config file not found. Copy config.yaml.example to config.yaml.")
        sys.exit(1)
    if args.output_dir:
        cfg.output_dir = args.output_dir
    if args.concurrent_limit is not None:
        cfg.concurrent_limit = args.concurrent_limit
    if args.request_timeout is not None:
        cfg.request_timeout = args.request_timeout

    if args.no_base64:
        cfg.write_base64 = False
    if args.no_singbox:
        cfg.write_singbox = False
    if args.no_clash:
        cfg.write_clash = False
    if args.write_html:
        cfg.write_html = True

    if args.output_surge is not None:
        cfg.surge_file = args.output_surge
    if args.output_qx is not None:
        cfg.qx_file = args.output_qx
    if args.output_xyz is not None:
        cfg.xyz_file = args.output_xyz
    if args.include_pattern:
        cfg.include_patterns.extend(args.include_pattern)
    if args.exclude_pattern:
        cfg.exclude_patterns.extend(args.exclude_pattern)
    cfg.shuffle_sources = getattr(args, "shuffle_sources", False)

    resolved_output = Path(cfg.output_dir).expanduser().resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    cfg.output_dir = str(resolved_output)

    resolved_log_dir = Path(cfg.log_dir).expanduser().resolve()
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    cfg.log_dir = str(resolved_log_dir)

    if args.protocols:
        protocols = [p.strip().lower() for p in args.protocols.split(",") if p.strip()]
    else:
        protocols = None

    setup_logging(Path(cfg.log_dir))

    if args.bot:
        asyncio.run(
            telegram_bot_mode(
                cfg,
                Path(args.sources),
                Path(args.channels),
                args.hours,
            )
        )
    else:

        out_dir, files = asyncio.run(
            run_pipeline(
                cfg,
                protocols,
                Path(args.sources),
                Path(args.channels),
                args.hours,
                failure_threshold=args.failure_threshold,
                prune=not args.no_prune,
            )
        )
        print(f"Aggregation complete. Files written to {out_dir.resolve()}")

        if args.upload_gist:
            token = cfg.github_token or os.environ.get("GITHUB_TOKEN")
            if not token:
                print("GitHub token not provided. Set github_token in config or GITHUB_TOKEN env var")
            else:
                links = asyncio.run(
                    output_writer.upload_files_to_gist(files, token)
                )
                path = output_writer.write_upload_links(links, out_dir)
                print(f"Uploaded files. Links saved to {path}")

        if args.with_merger:
            vpn_merger.CONFIG.resume_file = str(out_dir / "vpn_subscription_raw.txt")
            # propagate key settings from the aggregator config to the merger
            vpn_merger.CONFIG.output_dir = cfg.output_dir
            vpn_merger.CONFIG.write_base64 = cfg.write_base64
            vpn_merger.CONFIG.write_html = cfg.write_html
            vpn_merger.CONFIG.include_protocols = cfg.include_protocols
            vpn_merger.CONFIG.exclude_protocols = cfg.exclude_protocols
            vpn_merger.CONFIG.exclude_patterns = list(cfg.exclude_patterns)
            vpn_merger.CONFIG.concurrent_limit = cfg.concurrent_limit
            buf = io.StringIO()
            with redirect_stdout(buf):
                vpn_merger.detect_and_run()
            print("\n===== VPN Merger Summary =====")
            print(buf.getvalue().strip())


if __name__ == "__main__":
    main()
