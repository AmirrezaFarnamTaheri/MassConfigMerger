from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

from tqdm.asyncio import tqdm_asyncio

from ..config import Settings
from ..tester import NodeTester
from . import config_normalizer


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

    def __init__(self, settings: Settings) -> None:
        self.tester = NodeTester(settings)
        self.settings = settings

    def filter_configs(
        self, configs: Set[str], protocols: Optional[List[str]] = None
    ) -> Set[str]:
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
        host, port = config_normalizer.extract_host_port(cfg)
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
            return await tqdm_asyncio.gather(
                *tasks, total=len(tasks), desc="Testing configs"
            )
        finally:
            if self.tester:
                await self.tester.close()

    def create_semantic_hash(self, config: str) -> str:
        """Create semantic hash for intelligent deduplication."""
        return config_normalizer.create_semantic_hash(config)

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
        return config_normalizer.apply_tuning(config, self.settings)