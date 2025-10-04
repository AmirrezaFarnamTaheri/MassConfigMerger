from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import re
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse, parse_qs
from typing import Optional, Tuple, List, Set
import hashlib
from dataclasses import dataclass

from tqdm.asyncio import tqdm_asyncio

from ..config import Settings
from ..constants import MAX_DECODE_SIZE
from ..tester import NodeTester


@dataclass
class ConfigResult:
    """Data class for holding processed configuration results."""

    config: str
    protocol: str
    host: Optional[str] = None
    port: Optional[int] = None
    ping_time: Optional[float] = None
    is_reachable: bool = False
    source_url: str = ""
    country: Optional[str] = None


class ConfigProcessor:
    """A processor for testing and normalizing configurations."""

    MAX_DECODE_SIZE = MAX_DECODE_SIZE

    def __init__(self, settings: Settings) -> None:
        self.tester = NodeTester(settings)
        self.settings = settings

    def filter_configs(self, configs: Set[str], protocols: Optional[List[str]] = None) -> Set[str]:
        """Filter configurations based on protocol."""
        if not protocols:
            return configs

        protocols_upper = {p.upper() for p in protocols}

        filtered_configs = set()
        for config in configs:
            protocol = self.categorize_protocol(config).upper()
            if protocol in protocols_upper:
                filtered_configs.add(config)
        return filtered_configs

    async def _test_config(self, cfg: str) -> Tuple[str, Optional[float]]:
        host, port = self.extract_host_port(cfg)
        if host and port:
            ping = await self.tester.test_connection(host, port)
        else:
            ping = None
        return cfg, ping

    async def test_configs(
        self, configs: List[str]
    ) -> List[Tuple[str, Optional[float]]]:
        """Test a list of configurations for connectivity and latency."""
        semaphore = asyncio.Semaphore(self.settings.network.concurrent_limit)

        async def safe_worker(cfg: str) -> Tuple[str, Optional[float]]:
            async with semaphore:
                try:
                    return await self._test_config(cfg)
                except Exception as exc:
                    logging.debug("test_configs worker failed for %s: %s", cfg, exc)
                    return cfg, None

        tasks = [asyncio.create_task(safe_worker(c)) for c in configs]
        try:
            return await tqdm_asyncio.gather(*tasks, total=len(tasks), desc="Testing configs")
        finally:
            if self.tester:
                await self.tester.close()

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
                    decoded_bytes = base64.b64decode(padded)
                    if len(decoded_bytes) > self.MAX_DECODE_SIZE:
                        return urlunparse(
                            parsed._replace(query=sorted_query, fragment="")
                        )
                    decoded = decoded_bytes.decode("utf-8", "ignore")
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
                    decoded_bytes = base64.urlsafe_b64decode(padded)
                    if len(decoded_bytes) > self.MAX_DECODE_SIZE:
                        return None, None
                    decoded = decoded_bytes.decode()
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
                    decoded_bytes = base64.b64decode(padded)
                    if len(decoded_bytes) > self.MAX_DECODE_SIZE:
                        identifier = None
                    else:
                        decoded = decoded_bytes.decode("utf-8", "ignore")
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
                    decoded_bytes = base64.b64decode(padded)
                    if len(decoded_bytes) > self.MAX_DECODE_SIZE:
                        identifier = None
                    else:
                        decoded = decoded_bytes.decode("utf-8", "ignore")
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
            if self.settings.processing.mux_concurrency > 0:
                params["mux"] = [str(self.settings.processing.mux_concurrency)]
            if self.settings.processing.smux_streams > 0:
                params["smux"] = [str(self.settings.processing.smux_streams)]
            new_query = urlencode(params, doseq=True)
            return urlunparse(parsed._replace(query=new_query))
        except ValueError as exc:
            logging.debug("apply_tuning failed: %s", exc)
            return config