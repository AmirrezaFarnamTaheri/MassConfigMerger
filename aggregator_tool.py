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
import json
import logging
import os
import re
from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Set

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from telethon import TelegramClient, events, errors
from telethon.tl.custom.message import Message


CONFIG_FILE = Path("config.json")
SOURCES_FILE = Path("sources.txt")
CHANNELS_FILE = Path("channels.txt")

# Match full config links for supported protocols
PROTOCOL_RE = re.compile(
    r"(?:vmess|vless|trojan|ssr?|hysteria2?|tuic|reality|naive|hy2|wireguard)://\S+",
    re.IGNORECASE,
)
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=]+$")
HTTP_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def _get_script_dir() -> Path:
    """Return a safe base directory for writing output."""
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


def extract_subscription_urls(text: str) -> Set[str]:
    """Return all HTTP(S) URLs in the text block."""
    return set(HTTP_RE.findall(text))


def is_valid_config(link: str) -> bool:
    """Simple validation for known protocols."""
    if "warp://" in link:
        return False

    scheme, _, rest = link.partition("://")
    scheme = scheme.lower()
    rest = re.split(r"[?#]", rest, 1)[0]

    if scheme == "vmess":
        padded = rest + "=" * (-len(rest) % 4)
        try:
            json.loads(base64.b64decode(padded).decode())
            return True
        except Exception:
            return False
    host_required = {
        "naive",
        "hy2",
        "vless",
        "trojan",
        "reality",
        "hysteria",
        "hysteria2",
        "tuic",
        "ss",
        "ssr",
    }
    if scheme in host_required:
        if "@" not in rest:
            return False
        host = rest.split("@", 1)[1].split("/", 1)[0]
        return ":" in host
    if scheme == "wireguard":
        return bool(rest)

    return bool(rest)


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
    max_concurrent: int = 20

    @classmethod
    def load(
        cls, path: Path, defaults: dict | None = None
    ) -> "Config":
        """Load configuration from ``path`` applying optional defaults."""
        try:
            with path.open("r") as f:
                data = json.load(f)
        except FileNotFoundError as exc:
            raise ValueError(f"Config file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a JSON object")

        # Pull telegram credentials from environment and override when set
        env_values = {
            "telegram_api_id": os.getenv("TELEGRAM_API_ID"),
            "telegram_api_hash": os.getenv("TELEGRAM_API_HASH"),
            "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        }

        if env_values["telegram_api_id"] is not None:
            try:
                data["telegram_api_id"] = int(env_values["telegram_api_id"])
            except ValueError as exc:
                raise ValueError("TELEGRAM_API_ID must be an integer") from exc

        for key in ("telegram_api_hash", "telegram_bot_token"):
            if env_values[key] is not None:
                data[key] = env_values[key]

        merged_defaults = {
            "protocols": [],
            "exclude_patterns": [],
            "output_dir": "output",
            "log_dir": "logs",
            "max_concurrent": 20,
        }
        if defaults:
            merged_defaults.update(defaults)
        for key, value in merged_defaults.items():
            data.setdefault(key, value)

        required = [
            "telegram_api_id",
            "telegram_api_hash",
            "telegram_bot_token",
            "allowed_user_ids",
        ]
        known_fields = {f.name for f in fields(cls)}
        missing = [k for k in required if k not in data]
        unknown = [k for k in data if k not in known_fields]
        if missing or unknown:
            parts = []
            if missing:
                parts.append("missing required fields: " + ", ".join(missing))
            if unknown:
                parts.append("unknown fields: " + ", ".join(unknown))
            msg = f"Invalid config.json - {'; '.join(parts)}"
            raise ValueError(msg)

        try:
            return cls(**data)
        except (KeyError, TypeError) as exc:
            msg = f"Invalid configuration values: {exc}"
            print(msg)
            raise ValueError(msg) from exc



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
        matches = PROTOCOL_RE.findall(line)
        if matches:
            configs.update(matches)
            continue
        if BASE64_RE.match(line):
            try:
                decoded = base64.b64decode(line).decode()
                configs.update(PROTOCOL_RE.findall(decoded))
            except Exception:
                continue
    return configs


async def check_and_update_sources(path: Path, concurrent_limit: int = 20) -> List[str]:
    """Validate and deduplicate sources list concurrently."""
    if not path.exists():
        logging.warning("sources file not found: %s", path)
        return []

    with path.open() as f:
        sources = {line.strip() for line in f if line.strip()}

    valid_sources: List[str] = []
    semaphore = asyncio.Semaphore(concurrent_limit)
    connector = aiohttp.TCPConnector(limit=concurrent_limit)

    async def check(url: str) -> str | None:
        async with semaphore:
            text = await fetch_text(session, url)
        if not text:
            logging.info("Removing dead source: %s", url)
            return None
        if not parse_configs_from_text(text):
            logging.info("Removing empty source: %s", url)
            return None
        return url

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(check(u)) for u in sorted(sources)]
        for task in asyncio.as_completed(tasks):
            result = await task
            if result:
                valid_sources.append(result)


    with path.open("w") as f:
        for url in valid_sources:
            f.write(f"{url}\n")
    logging.info("Valid sources: %d", len(valid_sources))
    return valid_sources


async def fetch_and_parse_configs(
    sources: Iterable[str], max_concurrent: int = 20
) -> Set[str]:
    """Fetch configs from sources respecting concurrency limits."""
    configs: Set[str] = set()

    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(session: ClientSession, url: str) -> Set[str]:
        async with semaphore:
            text = await fetch_text(session, url)
        if not text:
            logging.warning("Failed to fetch %s", url)
            return set()
        return parse_configs_from_text(text)

    connector = aiohttp.TCPConnector(limit=max_concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(fetch_one(session, u)) for u in sources]
        for task in asyncio.as_completed(tasks):
            configs.update(await task)

    return configs


async def scrape_telegram_configs(channels_path: Path, last_hours: int, cfg: Config) -> Set[str]:
    """Scrape telegram channels for configs."""
    if not channels_path.exists():
        logging.warning("channels file missing: %s", channels_path)
        return set()
    with channels_path.open() as f:
        channels = [line.strip().removeprefix("https://t.me/") for line in f if line.strip()]

    if not channels:
        logging.info("No channels specified in %s", channels_path)
        return set()

    since = datetime.utcnow() - timedelta(hours=last_hours)
    client = TelegramClient("user", cfg.telegram_api_id, cfg.telegram_api_hash)
    configs: Set[str] = set()

    try:
        await client.start()
        async with aiohttp.ClientSession() as session:
            for channel in channels:
                count_before = len(configs)
                success = False
                for _ in range(2):
                    try:
                        async for msg in client.iter_messages(channel, offset_date=since):
                            if isinstance(msg, Message) and msg.message:
                                text = msg.message
                                configs.update(parse_configs_from_text(text))
                                for sub in extract_subscription_urls(text):
                                    text2 = await fetch_text(session, sub)
                                    if text2:
                                        configs.update(parse_configs_from_text(text2))
                        success = True
                        break
                    except (errors.RPCError, OSError) as e:
                        logging.warning("Error scraping %s: %s", channel, e)
                        try:
                            await client.disconnect()
                            await client.connect()
                        except Exception as rexc:
                            logging.warning("Reconnect failed: %s", rexc)
                            break
                if not success:
                    logging.warning("Skipping %s due to repeated errors", channel)
                    continue
                logging.info(
                    "Channel %s -> %d new configs",
                    channel,
                    len(configs) - count_before,
                )
        await client.disconnect()
    except Exception as e:
        logging.warning("Telegram connection failed: %s", e)
        try:
            await client.disconnect()
        except Exception:
            pass
        return set()

    logging.info("Telegram configs found: %d", len(configs))
    return configs


def deduplicate_and_filter(config_set: Set[str], cfg: Config, protocols: List[str] | None = None) -> List[str]:
    """Apply filters and return sorted configs."""
    final = []
    protocols = protocols or cfg.protocols
    exclude = [re.compile(p, re.IGNORECASE) for p in cfg.exclude_patterns]
    seen: Set[str] = set()
    for link in sorted(c.strip() for c in config_set):
        l_lower = link.lower()
        if l_lower in seen:
            continue
        seen.add(l_lower)
        if not any(l_lower.startswith(p + "://") for p in protocols):
            continue
        if any(r.search(l_lower) for r in exclude):
            continue
        if not is_valid_config(link):

            continue
        final.append(link)
    logging.info("Final configs count: %d", len(final))
    return final


def output_files(configs: List[str], out_dir: Path) -> None:
    """Write merged files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    merged_path = out_dir / "merged.txt"
    merged_b64 = out_dir / "merged_base64.txt"
    text = "\n".join(configs)
    merged_path.write_text(text)
    b64_content = base64.b64encode(text.encode()).decode()
    merged_b64.write_text(b64_content)

    # Validate base64 decodes cleanly
    try:
        base64.b64decode(b64_content).decode()
    except Exception:
        logging.warning("Base64 validation failed")

    # Simple sing-box style JSON
    outbounds = []
    for idx, link in enumerate(configs):
        proto = link.split("://", 1)[0].lower()
        outbounds.append({"type": proto, "tag": f"node-{idx}", "raw": link})
    (out_dir / "merged_singbox.json").write_text(
        json.dumps({"outbounds": outbounds}, indent=2, ensure_ascii=False)
    )

    logging.info("Wrote %s, %s and merged_singbox.json", merged_path, merged_b64)


async def run_pipeline(
    cfg: Config,
    protocols: List[str] | None = None,
    sources_file: Path = SOURCES_FILE,
    channels_file: Path = CHANNELS_FILE,
    last_hours: int = 24,
) -> Path:
    """Full aggregation pipeline. Returns output directory."""
    sources = await check_and_update_sources(sources_file, cfg.max_concurrent)
    configs = await fetch_and_parse_configs(sources, cfg.max_concurrent)
    configs |= await scrape_telegram_configs(channels_file, last_hours, cfg)

    final = deduplicate_and_filter(configs, cfg, protocols)
    out_dir = Path(cfg.output_dir)
    output_files(final, out_dir)
    return out_dir


async def telegram_bot_mode(
    cfg: Config,
    sources_file: Path = SOURCES_FILE,
    channels_file: Path = CHANNELS_FILE,
    last_hours: int = 24,
) -> None:

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
        out_dir = await run_pipeline(
            cfg,
            None,
            sources_file,
            channels_file,
            last_hours,
        )

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
    parser.add_argument("--config", default=str(CONFIG_FILE), help="path to config.json")
    parser.add_argument("--sources", default=str(SOURCES_FILE), help="path to sources.txt")
    parser.add_argument("--channels", default=str(CHANNELS_FILE), help="path to channels.txt")
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
        "--max-concurrent",
        type=int,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    cfg = Config.load(Path(args.config))
    if args.output_dir:
        cfg.output_dir = args.output_dir
    if args.concurrent_limit is not None:
        cfg.max_concurrent = args.concurrent_limit
    elif args.max_concurrent is not None:
        cfg.max_concurrent = args.max_concurrent

    allowed_base = _get_script_dir()
    resolved_output = Path(cfg.output_dir).expanduser().resolve()
    try:
        resolved_output.relative_to(allowed_base)
    except ValueError:
        parser.error(f"--output-dir must be within {allowed_base}")
    cfg.output_dir = str(resolved_output)

    if args.protocols:
        protocols = [p.strip() for p in args.protocols.split(",") if p.strip()]
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

        out_dir = asyncio.run(
            run_pipeline(
                cfg,
                protocols,
                Path(args.sources),
                Path(args.channels),
                args.hours,
            )
        )
        print(f"Aggregation complete. Files written to {out_dir.resolve()}")



if __name__ == "__main__":
    main()
