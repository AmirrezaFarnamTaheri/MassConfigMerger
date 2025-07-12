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
import json
import logging
import re
from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Set, Optional, Dict, Union, Tuple, cast
from urllib.parse import urlparse, parse_qs

import yaml

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from telethon import TelegramClient, events, errors  # type: ignore
from telethon.tl.custom.message import Message  # type: ignore
import vpn_merger

from constants import SOURCES_FILE

CONFIG_FILE = Path("config.json")
CHANNELS_FILE = Path("channels.txt")

# Match full config links for supported protocols
PROTOCOL_RE = re.compile(
    r"(?:"
    r"vmess|vless|reality|ssr?|trojan|hy2|hysteria2?|tuic|"
    r"shadowtls|juicity|naive|brook|wireguard|"
    r"socks5|socks4|socks|http|https|grpc|ws|wss|"
    r"tcp|kcp|quic|h2"
    r")://\S+",
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
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            logging.warning("Invalid vmess config: %s", exc)
            return False

    # ShadowsocksR links are base64 encoded after the scheme
    if scheme == "ssr":
        encoded = rest
        padded = encoded + "=" * (-len(encoded) % 4)
        try:
            decoded = base64.urlsafe_b64decode(padded).decode()
        except (binascii.Error, UnicodeDecodeError) as exc:
            logging.warning("Invalid ssr config encoding: %s", exc)
            return False
        host_part = decoded.split("/", 1)[0]
        if ":" not in host_part:
            return False
        host, port = host_part.split(":", 1)
        return bool(host and port)
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
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    allowed_user_ids: List[int] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    output_dir: str = "output"
    log_dir: str = "logs"
    request_timeout: int = 10
    max_concurrent: int = 20
    write_base64: bool = True
    write_singbox: bool = True
    write_clash: bool = True

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
        import os
        env_values = {
            "telegram_api_id": os.getenv("TELEGRAM_API_ID"),
            "telegram_api_hash": os.getenv("TELEGRAM_API_HASH"),
            "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
            "allowed_user_ids": os.getenv("ALLOWED_USER_IDS"),
        }

        if env_values["telegram_api_id"] is not None:
            try:
                data["telegram_api_id"] = int(env_values["telegram_api_id"])
            except ValueError as exc:
                raise ValueError("TELEGRAM_API_ID must be an integer") from exc

        for key in ("telegram_api_hash", "telegram_bot_token"):
            if env_values[key] is not None:
                data[key] = env_values[key]

        if env_values["allowed_user_ids"] is not None:
            try:
                ids = [
                    int(i)
                    for i in re.split(r"[ ,]+", env_values["allowed_user_ids"].strip())
                    if i
                ]
            except ValueError as exc:
                raise ValueError(
                    "ALLOWED_USER_IDS must be a comma separated list of integers"
                ) from exc
            data["allowed_user_ids"] = ids

        merged_defaults = {
            "protocols": [],
            "exclude_patterns": [],
            "output_dir": "output",
            "log_dir": "logs",
            "request_timeout": 10,
            "max_concurrent": 20,
            "write_base64": True,
            "write_singbox": True,
            "write_clash": True,
        }
        if defaults:
            merged_defaults.update(defaults)
        for key, value in merged_defaults.items():
            data.setdefault(key, value)

        known_fields = {f.name for f in fields(cls)}
        unknown = [k for k in data if k not in known_fields]
        if unknown:
            msg = "Invalid config.json - unknown fields: " + ", ".join(unknown)
            raise ValueError(msg)

        try:
            return cls(**data)
        except (KeyError, TypeError) as exc:
            msg = f"Invalid configuration values: {exc}"
            raise ValueError(msg) from exc



async def fetch_text(
    session: ClientSession, url: str, timeout: int = 10
) -> str | None:
    """Fetch text content from ``url`` with retries."""
    for _ in range(3):
        try:
            async with session.get(url, timeout=ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    return await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logging.debug("fetch_text error on %s: %s", url, exc)
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
            except (binascii.Error, UnicodeDecodeError) as exc:
                logging.debug("Failed to decode base64 line: %s", exc)
                continue
    return configs


async def check_and_update_sources(
    path: Path,
    concurrent_limit: int = 20,
    request_timeout: int = 10,
    failures_path: Path | None = None,
    max_failures: int = 3,
    prune: bool = True,
    disabled_path: Path | None = None,
) -> List[str]:
    """Validate and deduplicate sources list concurrently."""
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
        sources = {line.strip() for line in f if line.strip()}

    valid_sources: List[str] = []
    removed: List[str] = []
    semaphore = asyncio.Semaphore(concurrent_limit)
    connector = aiohttp.TCPConnector(limit=concurrent_limit)

    async def check(url: str) -> tuple[str, bool]:
        async with semaphore:
            text = await fetch_text(session, url, request_timeout)
        if not text or not parse_configs_from_text(text):
            return url, False
        return url, True

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(check(u)) for u in sorted(sources)]
        for task in asyncio.as_completed(tasks):
            url, ok = await task
            if ok:
                failures.pop(url, None)
                valid_sources.append(url)
            else:
                failures[url] = failures.get(url, 0) + 1
                if prune and failures[url] >= max_failures:
                    removed.append(url)

    remaining = [u for u in sorted(sources) if u not in removed]
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
    sources: Iterable[str], max_concurrent: int = 20, request_timeout: int = 10
) -> Set[str]:
    """Fetch configs from sources respecting concurrency limits."""
    configs: Set[str] = set()

    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(session: ClientSession, url: str) -> Set[str]:
        async with semaphore:
            text = await fetch_text(session, url, request_timeout)
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
    if cfg.telegram_api_id is None or cfg.telegram_api_hash is None:
        logging.info("Telegram credentials not provided; skipping Telegram scrape")
        return set()
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
                                    text2 = await fetch_text(session, sub, cfg.request_timeout)
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
                    continue
                logging.info(
                    "Channel %s -> %d new configs",
                    channel,
                    len(configs) - count_before,
                )
        await client.disconnect()
    except (errors.RPCError, OSError, aiohttp.ClientError) as e:
        logging.warning("Telegram connection failed: %s", e)
        try:
            await client.disconnect()
        except (errors.RPCError, OSError):
            pass
        return set()

    logging.info("Telegram configs found: %d", len(configs))
    return configs


def deduplicate_and_filter(
    config_set: Set[str], cfg: Config, protocols: List[str] | None = None
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
    seen: Set[str] = set()
    for link in sorted(c.strip() for c in config_set):
        l_lower = link.lower()
        if l_lower in seen:
            continue
        seen.add(l_lower)
        if protocols and not any(l_lower.startswith(p + "://") for p in protocols):
            continue
        if any(r.search(l_lower) for r in exclude):
            continue
        if not is_valid_config(link):

            continue
        final.append(link)
    logging.info("Final configs count: %d", len(final))
    return final


def output_files(configs: List[str], out_dir: Path, cfg: Config) -> List[Path]:
    """Write merged files and return list of written file paths respecting cfg flags."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    merged_path = out_dir / "merged.txt"
    text = "\n".join(configs)
    merged_path.write_text(text)
    written.append(merged_path)

    if cfg.write_base64:
        merged_b64 = out_dir / "merged_base64.txt"
        b64_content = base64.b64encode(text.encode()).decode()
        merged_b64.write_text(b64_content)
        written.append(merged_b64)

        # Validate base64 decodes cleanly
        try:
            base64.b64decode(b64_content).decode()
        except (binascii.Error, UnicodeDecodeError) as exc:
            logging.warning("Base64 validation failed: %s", exc)

    if cfg.write_singbox:
        # Simple sing-box style JSON
        outbounds = []
        for idx, link in enumerate(configs):
            proto = link.split("://", 1)[0].lower()
            outbounds.append({"type": proto, "tag": f"node-{idx}", "raw": link})
        merged_singbox = out_dir / "merged_singbox.json"
        merged_singbox.write_text(
            json.dumps({"outbounds": outbounds}, indent=2, ensure_ascii=False)
        )
        written.append(merged_singbox)

    def _config_to_clash_proxy(config: str, idx: int) -> Optional[Dict[str, Union[str, int, bool]]]:
        """Convert a single config link to a Clash proxy dictionary."""
        try:
            scheme = config.split("://", 1)[0].lower()
            name = f"{scheme}-{idx}"
            if scheme == "vmess":
                after = config.split("://", 1)[1]
                base = after.split("#", 1)[0]
                try:
                    padded = base + "=" * (-len(base) % 4)
                    data = json.loads(base64.b64decode(padded).decode())
                    name = data.get("ps") or data.get("name") or name
                    proxy = {
                        "name": name,
                        "type": "vmess",
                        "server": data.get("add") or data.get("host", ""),
                        "port": int(data.get("port", 0)),
                        "uuid": data.get("id") or data.get("uuid", ""),
                        "alterId": int(data.get("aid", 0)),
                        "cipher": data.get("type", "auto"),
                    }
                    if data.get("tls") or data.get("security"):
                        proxy["tls"] = True
                    return proxy
                except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                    logging.debug("Fallback Clash parse for vmess: %s", exc)
                    p = urlparse(config)
                    q = parse_qs(p.query)
                    proxy = {
                        "name": p.fragment or name,
                        "type": "vmess",
                        "server": p.hostname or "",
                        "port": p.port or 0,
                        "uuid": p.username or "",
                        "alterId": int(q.get("aid", [0])[0]),
                        "cipher": q.get("type", ["auto"])[0],
                    }
                security = q.get("security")
                if security:
                    proxy["tls"] = True
                return proxy
            elif scheme == "vless":
                p = urlparse(config)
                q = parse_qs(p.query)
                proxy = {
                    "name": p.fragment or name,
                    "type": "vless",
                    "server": p.hostname or "",
                    "port": p.port or 0,
                    "uuid": p.username or "",
                    "encryption": q.get("encryption", ["none"])[0],
                }
                security = q.get("security")
                if security:
                    proxy["tls"] = True
                return proxy
            elif scheme == "reality":
                p = urlparse(config)
                q = parse_qs(p.query)
                proxy = {
                    "name": p.fragment or name,
                    "type": "vless",
                    "server": p.hostname or "",
                    "port": p.port or 0,
                    "uuid": p.username or "",
                    "encryption": q.get("encryption", ["none"])[0],
                    "tls": True,
                }
                flow = q.get("flow")
                if flow:
                    proxy["flow"] = flow[0]
                return proxy
            elif scheme == "trojan":
                p = urlparse(config)
                q = parse_qs(p.query)
                proxy = {
                    "name": p.fragment or name,
                    "type": "trojan",
                    "server": p.hostname or "",
                    "port": p.port or 0,
                    "password": p.username or p.password or "",
                }
                sni = q.get("sni")
                if sni:
                    proxy["sni"] = sni[0]
                security = q.get("security")
                if security:
                    proxy["tls"] = True
                return proxy
            elif scheme in ("ss", "shadowsocks"):
                p = urlparse(config)
                if p.username and p.password and p.hostname and p.port:
                    method = p.username
                    password = p.password
                    server = p.hostname
                    port = p.port
                else:
                    base = config.split("://", 1)[1].split("#", 1)[0]
                    padded = base + "=" * (-len(base) % 4)
                    decoded = base64.b64decode(padded).decode()
                    before_at, host_port = decoded.split("@")
                    method, password = before_at.split(":")
                    server, port_str = host_port.split(":")
                    port = int(port_str)
                return {
                    "name": p.fragment or name,
                    "type": "ss",
                    "server": server,
                    "port": int(port),
                    "cipher": method,
                    "password": password,
                }
            elif scheme == "naive":
                p = urlparse(config)
                if not p.hostname or not p.port:
                    return None
                return {
                    "name": p.fragment or name,
                    "type": "http",
                    "server": p.hostname,
                    "port": p.port,
                    "username": p.username or "",
                    "password": p.password or "",
                    "tls": True,
                }
            else:
                p = urlparse(config)
                if not p.hostname or not p.port:
                    return None
                typ = "socks5" if scheme.startswith("socks") else "http"
                return {
                    "name": p.fragment or name,
                    "type": typ,
                    "server": p.hostname,
                    "port": p.port,
                }
        except (ValueError, binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            logging.debug("Failed to build Clash proxy: %s", exc)
            return None

    proxies = []
    if cfg.write_clash:
        for idx, link in enumerate(configs):
            proxy = _config_to_clash_proxy(link, idx)
            if proxy:
                proxies.append(proxy)
        if proxies:
            group = {"name": "Proxy", "type": "select", "proxies": [p["name"] for p in proxies]}
            clash_yaml = yaml.safe_dump(
                {"proxies": proxies, "proxy-groups": [group]},
                allow_unicode=True,
                sort_keys=False,
            )
            clash_file = out_dir / "clash.yaml"
            clash_file.write_text(clash_yaml)
            written.append(clash_file)

    logging.info(
        "Wrote %s%s%s%s",
        merged_path,
        ", merged_base64.txt" if cfg.write_base64 else "",
        ", merged_singbox.json" if cfg.write_singbox else "",
        ", clash.yaml" if cfg.write_clash and proxies else "",
    )

    return written


async def run_pipeline(
    cfg: Config,
    protocols: List[str] | None = None,
    sources_file: Path = SOURCES_FILE,
    channels_file: Path = CHANNELS_FILE,
    last_hours: int = 24,
    *,
    failure_threshold: int = 3,
    prune: bool = True,
) -> Tuple[Path, List[Path]]:
    """Full aggregation pipeline.
    Returns output directory and list of created files."""

    out_dir = Path(cfg.output_dir)
    configs: Set[str] = set()
    try:
        sources = await check_and_update_sources(
            sources_file,
            cfg.max_concurrent,
            cfg.request_timeout,
            failures_path=sources_file.with_suffix(".failures.json"),
            max_failures=failure_threshold,
            prune=prune,
            disabled_path=sources_file.with_name("sources_disabled.txt") if prune else None,
        )
        configs = await fetch_and_parse_configs(
            sources, cfg.max_concurrent, cfg.request_timeout
        )
        configs |= await scrape_telegram_configs(channels_file, last_hours, cfg)
    except KeyboardInterrupt:
        logging.warning("Interrupted. Writing partial results...")
    finally:
        final = deduplicate_and_filter(configs, cfg, protocols)
        files = output_files(final, out_dir, cfg)
    return out_dir, files


async def telegram_bot_mode(
    cfg: Config,
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
        TelegramClient("bot", cfg.telegram_api_id, cfg.telegram_api_hash).start(
            bot_token=cfg.telegram_bot_token
        ),
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
        out_dir, files = await run_pipeline(
            cfg,
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


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Mass VPN Config Aggregator. Telegram credentials are only required "
            "when scraping Telegram or running bot mode"
        )
    )
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
        "--request-timeout",
        type=int,
        help="HTTP request timeout in seconds",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--failure-threshold",
        type=int,
        default=3,
        help="consecutive failures before pruning a source",
    )
    parser.add_argument("--no-prune", action="store_true", help="do not remove failing sources")
    parser.add_argument("--no-base64", action="store_true", help="skip merged_base64.txt")
    parser.add_argument("--no-singbox", action="store_true", help="skip merged_singbox.json")
    parser.add_argument("--no-clash", action="store_true", help="skip clash.yaml")
    parser.add_argument(
        "--with-merger",
        action="store_true",
        help="run vpn_merger on the generated output directory after aggregation",
    )
    args = parser.parse_args()

    cfg = Config.load(Path(args.config))
    if args.output_dir:
        cfg.output_dir = args.output_dir
    if args.concurrent_limit is not None:
        cfg.max_concurrent = args.concurrent_limit
    elif args.max_concurrent is not None:
        cfg.max_concurrent = args.max_concurrent
    if args.request_timeout is not None:
        cfg.request_timeout = args.request_timeout

    if args.no_base64:
        cfg.write_base64 = False
    if args.no_singbox:
        cfg.write_singbox = False
    if args.no_clash:
        cfg.write_clash = False

    allowed_base = _get_script_dir()
    resolved_output = Path(cfg.output_dir).expanduser().resolve()
    try:
        resolved_output.relative_to(allowed_base)
    except ValueError:
        parser.error(f"--output-dir must be within {allowed_base}")
    cfg.output_dir = str(resolved_output)

    resolved_log_dir = Path(cfg.log_dir).expanduser().resolve()
    try:
        resolved_log_dir.relative_to(allowed_base)
    except ValueError:
        parser.error(f"log_dir must be within {allowed_base}")
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

        if args.with_merger:
            vpn_merger.detect_and_run(out_dir)



if __name__ == "__main__":
    main()
