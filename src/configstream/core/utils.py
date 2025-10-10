# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""Core utility functions for ConfigStream.

This module provides a collection of helper functions that are used across
the application for various tasks, including parsing, validation, sorting,
and networking. These utilities are designed to be self-contained and
reusable.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import math
import random
import re
import socket
from ipaddress import ip_address
from typing import Any, Callable, Set
from urllib.parse import urlparse

import aiohttp

from ..config import Settings
from ..constants import BASE64_RE, MAX_DECODE_SIZE, PROTOCOL_RE
from ..exceptions import ConfigError, NetworkError
from .config_processor import ConfigResult

SAFE_URL_SCHEMES = ("http", "https")
BLOCKED_HOSTS = (
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "169.254.169.254",
    "metadata.google.internal",
)
_warning_printed = False

# Pre-compile regex for extracting subscription URLs for performance.
URL_PATTERN = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate the great-circle distance between two points on the earth."""
    R = 6371  # Radius of earth in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) * math.sin(dLat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) * math.sin(dLon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_sort_key(
    settings: Settings,
) -> Callable[[ConfigResult], Any]:
    """
    Return a sort key function for sorting ConfigResult objects.
    """
    sort_by = settings.processing.sort_by
    if sort_by == "reliability":
        return lambda r: (
            not r.is_reachable,
            -r.reliability if r.reliability is not None else 0,
        )
    if sort_by == "proximity":
        user_lat = settings.processing.proximity_latitude
        user_lon = settings.processing.proximity_longitude
        if user_lat is None or user_lon is None:
            raise ValueError(
                "Proximity sorting requires user latitude and longitude.")

        return lambda r: (
            not r.is_reachable,
            haversine_distance(user_lat, user_lon, r.latitude, r.longitude)
            if r.latitude is not None and r.longitude is not None
            else float("inf"),
        )
    # Default to latency
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
    are defined. It also handles empty or whitespace-only proxy strings
    by treating them as None.

    Args:
        cfg: The application settings object.

    Returns:
        The proxy URL string, or None if no proxy is configured.
    Raises:
        ConfigError: If both http_proxy and socks_proxy are defined.
    """
    http_proxy = (cfg.network.http_proxy or "").strip() or None
    socks_proxy = (cfg.network.socks_proxy or "").strip() or None

    if http_proxy and socks_proxy:
        raise ConfigError(
            "http_proxy and socks_proxy cannot be used simultaneously")
    return socks_proxy or http_proxy


async def fetch_text(
    session,
    url: str,
    timeout: int = 10,
    *,
    retries: int = 3,
    base_delay: float = 1.0,
    jitter: float = 0.1,
    proxy: str | None = None,
) -> str:
    """
    Fetch text content from a URL with retries and exponential backoff.

    This function makes an HTTP GET request to the specified URL. If the
    request fails or returns a server-side error, it will retry with an
    exponentially increasing delay. This function includes SSRF protection
    by resolving the hostname to a safe IP address before connecting.

    Args:
        session: The aiohttp client session to use for the request.
        url: The URL to fetch.
        timeout: The total timeout for the request in seconds.
        retries: The maximum number of retry attempts.
        base_delay: The base delay for the exponential backoff in seconds.
        jitter: A random factor to add to the delay to avoid thundering herd problems.
        proxy: The proxy URL to use for the request.

    Returns:
        The text content of the response.
    Raises:
        NetworkError: If the request fails after all retries or if SSRF checks fail.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise NetworkError(f"Invalid URL for fetch_text: {url}")

    # --- SSRF Mitigation ---
    hostname = parsed.hostname
    if not hostname or hostname in BLOCKED_HOSTS:
        raise NetworkError(
            f"Blocked or invalid hostname for security reasons: {hostname}")
    if parsed.scheme not in SAFE_URL_SCHEMES:
        raise NetworkError(f"Invalid URL scheme: {parsed.scheme}")

    # Resolve hostname to IP addresses
    try:
        loop = asyncio.get_running_loop()
        addrinfos = await loop.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise NetworkError(f"DNS resolution failed for {hostname}") from e

    # Find the first public IP address
    safe_ip = None
    for _, _, _, _, sockaddr in addrinfos:
        ip = ip_address(sockaddr[0])
        if not (
            ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_unspecified
        ):
            safe_ip = str(ip)
            break

    if not safe_ip:
        raise NetworkError(f"No safe, public IP address found for {hostname}")

    # Reconstruct the URL with the resolved IP and set the Host header
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    request_url = parsed._replace(
        netloc=f"{safe_ip}:{port}", path=path).geturl()
    request_headers = {"Host": hostname}
    # --- End SSRF Mitigation ---

    last_exc = None
    attempt = 0
    while attempt < retries:
        try:
            async with session.get(
                request_url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                proxy=proxy,
                headers=request_headers,
            ) as resp:
                if resp.status == 200:
                    return await resp.text(errors="ignore")
                if 400 <= resp.status < 500 and resp.status != 429:
                    raise NetworkError(
                        f"Non-retryable client error for {url}: {resp.status}"
                    )
                last_exc = aiohttp.ClientResponseError(
                    resp.request_info,
                    resp.history,
                    status=resp.status,
                    message=await resp.text(),
                    headers=resp.headers,
                )
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logging.debug("fetch_text error on %s: %s", url, exc)
            last_exc = exc

        attempt += 1
        if attempt >= retries:
            break

        # Exponential backoff with jitter
        backoff = base_delay * (2 ** (attempt - 1))
        sleep_duration = backoff + (backoff * random.uniform(0, jitter))

        logging.debug(
            "Attempt %d/%d failed for %s. Retrying in %.2f seconds...",
            attempt,
            retries,
            url,
            sleep_duration,
        )
        await asyncio.sleep(sleep_duration)

    raise NetworkError(
        f"Failed to fetch {url} after {retries} retries.") from last_exc


def is_safe_url(url: str) -> bool:
    """
    Check if a URL is safe to fetch.

    This function validates the URL scheme against a whitelist and checks
    the hostname against a blacklist of reserved or local addresses.

    Args:
        url: The URL to validate.

    Returns:
        True if the URL is safe, False otherwise.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in SAFE_URL_SCHEMES:
            return False
        if not parsed.hostname or parsed.hostname in BLOCKED_HOSTS:
            return False
    except (ValueError, AttributeError):
        return False
    return True
