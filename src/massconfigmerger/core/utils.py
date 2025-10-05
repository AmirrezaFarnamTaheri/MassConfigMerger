"""Core utility functions for MassConfigMerger.

This module provides a collection of helper functions that are used across
the application for various tasks, including parsing, validation, sorting,
and networking. These utilities are designed to be self-contained and
reusable.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import random
import re
from typing import Any, Callable, Set
from urllib.parse import urlparse

import aiohttp

from ..config import Settings
from ..constants import BASE64_RE, MAX_DECODE_SIZE, PROTOCOL_RE
from .config_processor import ConfigResult

_warning_printed = False

# Pre-compile regex for extracting subscription URLs for performance.
URL_PATTERN = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')


def get_sort_key(sort_by: str) -> Callable[[ConfigResult], Any]:
    """
    Return a sort key function for sorting ConfigResult objects.

    This function generates a key for Python's `sort` or `sorted` functions
    based on the desired metric. The sorting always prioritizes reachability,
    ensuring that unreachable configurations are placed at the end of the list.

    Args:
        sort_by: The metric to sort by. Supported values are 'latency'
                 and 'reliability'.

    Returns:
        A callable that takes a `ConfigResult` object and returns a
        sortable tuple.
    """
    if sort_by == "reliability":
        # Sort by reachability (False comes first), then by reliability (higher is better)
        return lambda r: (
            not r.is_reachable,
            -r.reliability if r.reliability is not None else 0,
        )
    # Default to sorting by latency (lower is better)
    return lambda r: (
        not r.is_reachable,
        r.ping_time if r.ping_time is not None else float("inf"),
    )


def extract_subscription_urls(text: str) -> Set[str]:
    """
    Extract all http/https URLs from a block of text.

    This function uses a regular expression to find all potential URLs and
    then cleans them by removing common trailing punctuation that may have
    been included by the regex.

    Args:
        text: A string containing potential URLs.

    Returns:
        A set of cleaned, unique URLs found in the text.
    """
    # We need to manually clean trailing punctuation as the regex can be greedy
    raw_urls = URL_PATTERN.findall(text)
    cleaned_urls = set()
    for url in raw_urls:
        # Repeatedly strip trailing punctuation that might be attached to the URL
        while url and url[-1] in '.,!?:;)]':
            url = url[:-1]
        cleaned_urls.add(url)
    return cleaned_urls


def print_public_source_warning() -> None:
    """
    Print a security and usage warning to the console once per execution.

    This function uses a global flag to ensure that the warning message is
    only displayed once, preventing repetitive output in long-running
    processes or applications with multiple entry points.
    """
    global _warning_printed
    if not _warning_printed:
        print(
            "WARNING: Collected VPN nodes come from public sources. "
            "Use at your own risk and comply with local laws."
        )
        _warning_printed = True


def is_valid_config(link: str) -> bool:
    """
    Perform a simple validation check on a configuration link.

    This function checks for basic structural validity based on the protocol
    scheme. It is not exhaustive but helps to filter out clearly malformed
    links early in the process.

    Args:
        link: The configuration link to validate.

    Returns:
        True if the link appears to be valid, False otherwise.
    """
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
    """
    Extract all VPN configuration links from a block of text.

    This function searches for links with known protocol schemes. It also
    attempts to find and decode base64-encoded content, from which it then
    extracts configuration links.

    Args:
        text: The text content to parse.

    Returns:
        A set of unique configuration links found in the text.
    """
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
    """
    Return the appropriate proxy URL from settings.

    This function prioritizes the SOCKS proxy over the HTTP proxy if both
    are defined in the application settings.

    Args:
        cfg: The application settings object.

    Returns:
        The proxy URL string, or None if no proxy is configured.
    """
    return cfg.network.socks_proxy or cfg.network.http_proxy


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
    """
    Fetch text content from a URL with retries and exponential backoff.

    This function makes an HTTP GET request to the specified URL. If the
    request fails or returns a server-side error, it will retry with an
    exponentially increasing delay.

    Args:
        session: The aiohttp client session to use for the request.
        url: The URL to fetch.
        timeout: The total timeout for the request in seconds.
        retries: The maximum number of retry attempts.
        base_delay: The base delay for the exponential backoff in seconds.
        jitter: A random factor to add to the delay to avoid thundering herd problems.
        proxy: The proxy URL to use for the request.

    Returns:
        The text content of the response, or None if the request fails
        after all retries.
    """
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