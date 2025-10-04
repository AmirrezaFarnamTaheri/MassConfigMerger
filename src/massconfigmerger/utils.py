"""Utility helpers for protocol detection and parsing."""

from __future__ import annotations

import base64
import binascii
import json
import logging
import re
from urllib.parse import urlparse
from typing import Set

from .config import Settings

from .constants import PROTOCOL_RE, BASE64_RE, MAX_DECODE_SIZE

_warning_printed = False


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
            json.loads(base64.b64decode(padded, validate=True).decode())
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
        host = rest.split("@", 1)[1].split("/", 1)[0]
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


from dataclasses import dataclass
import hashlib
from .tester import NodeTester
from urllib.parse import parse_qsl, urlencode, urlunparse


def choose_proxy(cfg: Settings) -> str | None:
    """Return SOCKS proxy if defined, otherwise HTTP proxy."""
    return cfg.SOCKS_PROXY or cfg.HTTP_PROXY


@dataclass
class ConfigResult:
    """Enhanced config result with testing metrics."""

    config: str
    protocol: str
    host: Optional[str] = None
    port: Optional[int] = None
    ping_time: Optional[float] = None
    is_reachable: bool = False
    source_url: str = ""
    country: Optional[str] = None


class EnhancedConfigProcessor:
    """Advanced configuration processor with comprehensive testing capabilities."""

    MAX_DECODE_SIZE = MAX_DECODE_SIZE

    def __init__(self, settings: Settings) -> None:
        self.tester = NodeTester(settings)
        self.settings = settings

    def _normalize_url(self, config: str) -> str:
        """Return canonical URL with sorted query params and no fragment."""
        parsed = urlparse(config)
        query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
        sorted_query = urlencode(sorted(query_pairs), doseq=True)

        scheme = parsed.scheme.lower()
        if scheme in {"vmess", "vless"}:
            payload = parsed.netloc or parsed.path.lstrip("/")
            if payload:
                try:
                    padded = payload + "=" * (-len(payload) % 4)
                    decoded = base64.b64decode(padded).decode("utf-8", "ignore")
                    data = json.loads(decoded)
                    canonical_json = json.dumps(data, sort_keys=True)
                    payload = (
                        base64.b64encode(canonical_json.encode())
                        .decode()
                        .rstrip("=")
                    )
                    parsed = parsed._replace(netloc=payload, path="")
                except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
                    pass

        return urlunparse(parsed._replace(query=sorted_query, fragment=""))

    def extract_host_port(self, config: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract host and port from configuration for testing."""
        try:
            if config.startswith(("vmess://", "vless://")):
                try:
                    json_part = config.split("://", 1)[1]
                    decoded_bytes = base64.b64decode(json_part)
                    if len(decoded_bytes) > self.MAX_DECODE_SIZE:
                        return None, None
                    decoded = decoded_bytes.decode("utf-8", "ignore")
                    data = json.loads(decoded)
                    host = data.get("add") or data.get("host")
                    port = data.get("port")
                    return host, int(port) if port else None
                except (
                    binascii.Error,
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                    ValueError,
                ) as exc:
                    logging.debug("extract_host_port vmess failed: %s", exc)

            if config.startswith("ssr://"):
                try:
                    after = config.split("://", 1)[1].split("#", 1)[0]
                    padded = after + "=" * (-len(after) % 4)
                    decoded = base64.urlsafe_b64decode(padded).decode()
                    host_part = decoded.split("/", 1)[0]
                    parts = host_part.split(":")
                    if len(parts) < 2:
                        return None, None
                    host, port = parts[0], parts[1]
                    return host or None, int(port)
                except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
                    logging.debug("extract_host_port ssr failed: %s", exc)

            parsed = urlparse(config)
            if parsed.hostname and parsed.port:
                return parsed.hostname, parsed.port

            match = re.search(r"@([^:/?#]+):(\d+)", config)
            if match:
                return match.group(1), int(match.group(2))

        except (ValueError, UnicodeError, binascii.Error) as exc:
            logging.debug("extract_host_port failed: %s", exc)
        return None, None

    def create_semantic_hash(self, config: str) -> str:
        """Create semantic hash for intelligent deduplication."""
        parsed = urlparse(config)
        normalized_config = self._normalize_url(config)

        host, port = self.extract_host_port(normalized_config)
        identifier = None

        scheme = parsed.scheme.lower()

        if scheme in ("vmess", "vless"):
            try:
                after_scheme = normalized_config.split("://", 1)[1].split("?", 1)[0]
                if parsed.username:
                    identifier = parsed.username
                else:
                    padded = after_scheme + "=" * (-len(after_scheme) % 4)
                    decoded = base64.b64decode(padded).decode("utf-8", "ignore")
                    data = json.loads(decoded)
                    json.dumps(data, sort_keys=True)
                    identifier = data.get("id") or data.get("uuid") or data.get("user")
            except (
                binascii.Error,
                UnicodeDecodeError,
                json.JSONDecodeError,
                ValueError,
            ) as exc:
                logging.debug("semantic_hash vmess failed: %s", exc)
        elif scheme == "trojan":
            try:
                parsed = urlparse(normalized_config)
                if parsed.username or parsed.password:
                    identifier = parsed.username or ""
                    if parsed.password is not None:
                        if identifier:
                            identifier += f":{parsed.password}"
                        else:
                            identifier = parsed.password
                else:
                    identifier = None
            except ValueError as exc:
                logging.debug("semantic_hash trojan failed: %s", exc)
        elif scheme in ("ss", "shadowsocks"):
            try:
                parsed = urlparse(normalized_config)
                if parsed.username and parsed.password:
                    identifier = parsed.password
                else:
                    base = normalized_config.split("://", 1)[1]
                    base = base.split("?", 1)[0]
                    padded = base + "=" * (-len(base) % 4)
                    decoded = base64.b64decode(padded).decode("utf-8", "ignore")
                    before_at = decoded.split("@", 1)[0]
                    _, password = before_at.split(":", 1)
                    identifier = password
            except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
                logging.debug("semantic_hash ss failed: %s", exc)

        if host and port:
            key = f"{host}:{port}"
            if identifier:
                key = f"{identifier}@{key}"
        else:
            key = normalized_config.strip()
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    async def test_connection(self, host: str, port: int) -> Optional[float]:
        """Test connection and measure response time using :class:`NodeTester`."""
        return await self.tester.test_connection(host, port)

    async def lookup_country(self, host: str) -> Optional[str]:
        """Return ISO country code for ``host`` using :class:`NodeTester`."""
        return await self.tester.lookup_country(host)

    def categorize_protocol(self, config: str) -> str:
        """Categorize configuration by protocol."""
        protocol_map = {
            "vmess://": "VMess",
            "vless://": "VLESS",
            "ss://": "Shadowsocks",
            "ssr://": "ShadowsocksR",
            "trojan://": "Trojan",
            "hy2://": "Hysteria2",
            "hysteria2://": "Hysteria2",
            "hysteria://": "Hysteria",
            "tuic://": "TUIC",
            "reality://": "Reality",
            "naive://": "Naive",
            "juicity://": "Juicity",
            "wireguard://": "WireGuard",
            "shadowtls://": "ShadowTLS",
            "brook://": "Brook",
        }
        config_lower = config.lower()
        for prefix, protocol in protocol_map.items():
            if config_lower.startswith(prefix):
                return protocol
        return "Other"

    def apply_tuning(self, config: str) -> str:
        """Apply mux and smux parameters to URI-style configs."""
        try:
            if "//" not in config or config.startswith("vmess://"):
                return config
            parsed = urlparse(config)
            if not parsed.scheme:
                return config
            params = parse_qs(parsed.query)
            if self.settings.mux_concurrency > 0:
                params["mux"] = [str(self.settings.mux_concurrency)]
            if self.settings.smux_streams > 0:
                params["smux"] = [str(self.settings.smux_streams)]
            new_query = urlencode(params, doseq=True)
            return urlunparse(parsed._replace(query=new_query))
        except ValueError as exc:
            logging.debug("apply_tuning failed: %s", exc)
            return config


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
