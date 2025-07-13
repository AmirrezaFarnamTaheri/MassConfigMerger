from __future__ import annotations

import asyncio
import logging
import random
import re
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientSession, ClientTimeout

# Regex patterns for configuration URLs
PROTOCOL_RE = re.compile(
    r"(?:"
    r"vmess|vless|reality|ssr?|trojan|hy2|hysteria2?|tuic|"
    r"shadowtls|juicity|naive|brook|wireguard|"
    r"socks5|socks4|socks|http|https|grpc|ws|wss|"
    r"tcp|kcp|quic|h2"
    r")://\S+",
    re.IGNORECASE,
)
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=_-]+$")
HTTP_RE = re.compile(r"https?://\S+", re.IGNORECASE)

# Safety limit for base64 decoding to avoid huge payloads
MAX_DECODE_SIZE = 256 * 1024  # 256 kB


async def fetch_text(
    session: ClientSession,
    url: str,
    timeout: int = 10,
    *,
    retries: int = 3,
    base_delay: float = 1.0,
    jitter: float = 0.1,
    proxy: str | None = None,
) -> str | None:
    """Fetch text content from ``url`` with retries and exponential backoff."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        logging.debug("fetch_text invalid url: %s", url)
        return None

    attempt = 0
    use_temp = hasattr(session, "loop") and session.loop is not asyncio.get_running_loop()
    if use_temp:
        session = aiohttp.ClientSession(proxy=proxy) if proxy else aiohttp.ClientSession()
    while attempt < retries:
        try:
            async with session.get(url, timeout=ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    return await resp.text()
                if 400 <= resp.status < 500 and resp.status != 429:
                    logging.debug("fetch_text non-retry status %s on %s", resp.status, url)
                    return None
                if not (500 <= resp.status < 600 or resp.status == 429):
                    logging.debug(
                        "fetch_text non-transient status %s on %s", resp.status, url
                    )
                    return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logging.debug("fetch_text error on %s: %s", url, exc)

        attempt += 1
        if attempt >= retries:
            break
        delay = base_delay * 2 ** (attempt - 1)
        await asyncio.sleep(delay + random.uniform(0, jitter))
    if use_temp:
        await session.close()
    return None
