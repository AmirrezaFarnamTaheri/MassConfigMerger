"""Utility helpers for protocol detection and parsing."""

from __future__ import annotations

import base64
import binascii
import json
import logging
import re
from urllib.parse import urlparse
from typing import Set

from ..config import Settings
from ..constants import PROTOCOL_RE, BASE64_RE, MAX_DECODE_SIZE

_warning_printed = False


def extract_subscription_urls(text: str) -> Set[str]:
    """Extract all http/https URLs from a text block, cleaning them."""
    # This regex is designed to be simple and effective for this use case.
    # It captures http/https URLs and avoids including common trailing punctuation.
    url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')

    # We need to manually clean trailing punctuation as the regex can be greedy
    raw_urls = url_pattern.findall(text)
    cleaned_urls = set()
    for url in raw_urls:
        # Repeatedly strip trailing punctuation that might be attached to the URL
        while url and url[-1] in '.,!?:;)]':
            url = url[:-1]
        cleaned_urls.add(url)
    return cleaned_urls


def print_public_source_warning() -> None:
    """Print a usage warning once per execution."""
    global _warning_printed
    if not _warning_printed:
        print(
            "WARNING: Collected VPN nodes come from public sources. "
            "Use at your own risk and comply with local laws."
        )
        _warning_printed = True


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
            decoded = base64.urlsafe_b64decode(padded).decode()
            json.loads(decoded)
            return True
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            logging.warning("Invalid vmess config: %s", exc)
            return False

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
        user_info, host_part = rest.split("@", 1)
        host = host_part.split("/", 1)[0]
        if scheme == "ss" and ":" not in user_info:
            return False
        return ":" in host

    simple_host_port = {
        "http",
        "https",
        "grpc",
        "ws",
        "wss",
        "socks",
        "socks4",
        "socks5",
        "tcp",
        "kcp",
        "quic",
        "h2",
    }
    if scheme in simple_host_port:
        parsed = urlparse(link)
        return bool(parsed.hostname and parsed.port)
    if scheme == "wireguard":
        return bool(rest)

    return bool(rest)


def parse_configs_from_text(text: str) -> Set[str]:
    """Extract all config links from a text block."""
    configs: Set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        matches = PROTOCOL_RE.findall(line)
        if matches:
            configs.update(m.rstrip('\'".,!?:;)') for m in matches)
            continue
        if BASE64_RE.match(line):
            if len(line) > MAX_DECODE_SIZE:
                logging.debug(
                    "Skipping oversized base64 line (%d > %d)",
                    len(line),
                    MAX_DECODE_SIZE,
                )
                continue
            try:
                padded = line + "=" * (-len(line) % 4)
                decoded = base64.urlsafe_b64decode(padded).decode()
                base64_matches = PROTOCOL_RE.findall(decoded)
                configs.update(m.rstrip('\'".,!?:;)') for m in base64_matches)
            except (binascii.Error, UnicodeDecodeError) as exc:
                logging.debug("Failed to decode base64 line: %s", exc)
                continue
    return configs


def choose_proxy(cfg: Settings) -> str | None:
    """Return SOCKS proxy if defined, otherwise HTTP proxy."""
    return cfg.network.SOCKS_PROXY or cfg.network.HTTP_PROXY


async def fetch_text(
    session,
    url: str,
    timeout: int = 10,
    *,
    retries: int = 3,
    base_delay: float = 1.0,
    jitter: float = 0.1,
    proxy: str | None = None,
) -> str | None:
    """Fetch text content from ``url`` with retries and exponential backoff."""
    import aiohttp
    import asyncio
    import random

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        logging.debug("fetch_text invalid url: %s", url)
        return None

    attempt = 0
    while attempt < retries:
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout), proxy=proxy
            ) as resp:
                if resp.status == 200:
                    return await resp.text(errors="ignore")
                if 400 <= resp.status < 500 and resp.status != 429:
                    logging.debug(
                        "fetch_text non-retry status %s on %s", resp.status, url
                    )
                    return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logging.debug("fetch_text error on %s: %s", url, exc)

        attempt += 1
        if attempt >= retries:
            break
        delay = base_delay * 2 ** (attempt - 1)
        await asyncio.sleep(delay + random.uniform(0, jitter))

    return None