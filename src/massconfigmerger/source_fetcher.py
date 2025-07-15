from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import random
import re
from pathlib import Path
from typing import List, Optional, Tuple, Set, Callable, Awaitable, Union
from urllib.parse import urlparse

import aiohttp
from tqdm import tqdm

from .constants import SOURCES_FILE
from .result_processor import CONFIG, EnhancedConfigProcessor, ConfigResult

# Regex patterns for extracting configuration links during pre-flight checks
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
MAX_DECODE_SIZE = 256 * 1024  # 256 kB


async def fetch_text(
    session: aiohttp.ClientSession,
    url: str,
    timeout: int = 10,
    *,
    retries: int = 3,
    base_delay: float = 1.0,
    jitter: float = 0.1,
) -> str | None:
    """Fetch text content with retries."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        logging.debug("fetch_text invalid url: %s", url)
        return None

    attempt = 0
    while attempt < retries:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
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
    return None


def parse_first_configs(text: str, limit: int = 5) -> List[str]:
    """Extract up to ``limit`` configuration links from ``text``."""
    configs: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        matches = PROTOCOL_RE.findall(line)
        if matches:
            for m in matches:
                configs.append(m)
                if len(configs) >= limit:
                    return configs
            continue
        if BASE64_RE.match(line):
            if len(line) > MAX_DECODE_SIZE:
                continue
            try:
                padded = line + "=" * (-len(line) % 4)
                decoded = base64.urlsafe_b64decode(padded).decode()
                for m in PROTOCOL_RE.findall(decoded):
                    configs.append(m)
                    if len(configs) >= limit:
                        return configs
            except (binascii.Error, UnicodeDecodeError):
                continue
    return configs


class UnifiedSources:
    """Load VPN subscription sources from an external file."""

    DEFAULT_FILE = SOURCES_FILE
    FALLBACK_SOURCES = [
        "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub1.txt",
        "https://raw.githubusercontent.com/ssrsub/ssr/master/v2ray",
        "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/splitted/vmess.txt",
    ]

    @classmethod
    def load(cls, path: Optional[Union[str, Path]] = None) -> List[str]:
        file_path = Path(path) if path else cls.DEFAULT_FILE
        if file_path.exists():
            with file_path.open() as f:
                return [line.strip() for line in f if line.strip()]
        logging.warning("sources file not found: %s; using fallback list", file_path)
        return cls.FALLBACK_SOURCES

    @classmethod
    def get_all_sources(cls, path: Optional[Union[str, Path]] = None) -> List[str]:
        """Return list of sources from file or fallback."""
        return cls.load(path)


class AsyncSourceFetcher:
    """Async source fetcher with comprehensive testing and availability checking."""

    def __init__(
        self,
        processor: EnhancedConfigProcessor,
        seen_hashes: Set[str],
        hash_lock: Optional[asyncio.Lock] = None,
        history_callback: Optional[
            Callable[[str, bool, Optional[float]], Awaitable[None]]
        ] = None,
    ):
        self.processor = processor
        self.session: Optional[aiohttp.ClientSession] = None
        self.seen_hashes = seen_hashes
        self.hash_lock = hash_lock or asyncio.Lock()
        self.history_callback = history_callback
        self.progress: Optional[tqdm] = None

    async def test_source_availability(self, url: str) -> bool:
        """Test if a source URL is available (returns 200 status)."""
        session = self.session
        if session is None:
            loop_check = None
        elif hasattr(session, "get_loop"):
            loop_check = session.get_loop()
        else:
            loop_check = asyncio.get_running_loop()
        if session is None or loop_check is not asyncio.get_running_loop():
            session = aiohttp.ClientSession()
            close_temp = True
        else:
            close_temp = False
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.head(url, timeout=timeout, allow_redirects=True) as response:
                status = response.status
                if status == 200:
                    return True
                if 400 <= status < 500:
                    async with session.get(
                        url,
                        headers={**CONFIG.headers, 'Range': 'bytes=0-0'},
                        timeout=timeout,
                        allow_redirects=True,
                    ) as get_resp:
                        return get_resp.status in (200, 206)
                return False
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logging.debug("availability check failed for %s: %s", url, exc)
            return False
        finally:
            if close_temp:
                await session.close()

    async def fetch_source(self, url: str) -> Tuple[str, List[ConfigResult]]:
        """Fetch single source with comprehensive testing and deduplication."""
        session = self.session
        if session is None:
            loop_check = None
        elif hasattr(session, "get_loop"):
            loop_check = session.get_loop()
        else:
            loop_check = asyncio.get_running_loop()
        use_temp = session is None or loop_check is not asyncio.get_running_loop()
        if use_temp:
            session = aiohttp.ClientSession()
        for attempt in range(CONFIG.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=CONFIG.request_timeout)
                async with session.get(url, headers=CONFIG.headers, timeout=timeout) as response:
                    if response.status != 200:
                        continue

                    content = await response.text()
                    if not content.strip():
                        return url, []

                    try:
                        if not any(char in content for char in '\n\r') and len(content) > 100:
                            decoded = base64.b64decode(content).decode("utf-8", "ignore")
                            if decoded.count("://") > content.count("://"):
                                content = decoded
                    except (binascii.Error, UnicodeDecodeError) as exc:
                        logging.debug("Base64 decode failed: %s", exc)

                    lines = [line.strip() for line in content.splitlines() if line.strip()]
                    config_results: List[ConfigResult] = []

                    iterator = (
                        tqdm(lines, desc="Testing", leave=False, unit="cfg")
                        if CONFIG.enable_url_testing
                        else lines
                    )
                    for line in iterator:
                        if all(
                            [
                                line.startswith(CONFIG.valid_prefixes),
                                len(line) > 20,
                                len(line) < 2000,
                                len(config_results) < CONFIG.max_configs_per_source,
                            ]
                        ):
                            config_hash = self.processor.create_semantic_hash(line)
                            async with self.hash_lock:
                                if config_hash in self.seen_hashes:
                                    continue
                                self.seen_hashes.add(config_hash)

                            line = self.processor.apply_tuning(line)

                            host, port = self.processor.extract_host_port(line)
                            protocol = self.processor.categorize_protocol(line)

                            country = await self.processor.lookup_country(host) if host else None
                            result = ConfigResult(
                                config=line,
                                protocol=protocol,
                                host=host,
                                port=port,
                                source_url=url,
                                country=country
                            )

                            if CONFIG.enable_url_testing and host and port:
                                ping_time = await self.processor.test_connection(host, port)
                                result.ping_time = ping_time
                                result.is_reachable = ping_time is not None
                                if self.history_callback:
                                    await self.history_callback(
                                        config_hash,
                                        result.is_reachable,
                                        ping_time,
                                    )

                            config_results.append(result)
                            if self.progress is not None:
                                self.progress.update(1)
                                self.progress.set_postfix(
                                    processed=self.progress.n,
                                    remaining=self.progress.total - self.progress.n,
                                    refresh=False,
                                )

                    if iterator is not lines and hasattr(iterator, "close"):
                        iterator.close()

                    return url, config_results

            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                logging.debug("fetch_source error on %s: %s", url, exc)
                if attempt < CONFIG.max_retries - 1:
                    await asyncio.sleep(min(3, 1.5 + random.random()))
        if use_temp:
            await session.close()
        return url, []
