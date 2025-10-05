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
    reliability: Optional[float] = None


class ConfigProcessor:
    """A processor for testing and normalizing configurations."""

    def __init__(self, settings: Settings) -> None:
        self.tester = NodeTester(settings)
        self.settings = settings

    def filter_configs(
        self, configs: Set[str], *, use_fetch_rules: bool = False
    ) -> Set[str]:
        """Filter configurations based on protocol rules in settings."""
        if use_fetch_rules:
            # Use fetch_protocols for simple inclusion filtering.
            include_protos = {p.upper() for p in self.settings.filtering.fetch_protocols}
            if not include_protos:
                return configs
            return {
                cfg for cfg in configs if self.categorize_protocol(cfg).upper() in include_protos
            }
        else:
            # Use merge_include/exclude_protocols for more complex filtering.
            include_protos = self.settings.filtering.merge_include_protocols
            exclude_protos = self.settings.filtering.merge_exclude_protocols
            if not include_protos and not exclude_protos:
                return configs

            filtered = set()
            for cfg in configs:
                proto = self.categorize_protocol(cfg).upper()
                if include_protos and proto not in include_protos:
                    continue
                if exclude_protos and proto in exclude_protos:
                    continue
                filtered.add(cfg)
            return filtered

    async def _test_config(self, cfg: str) -> ConfigResult:
        host, port = config_normalizer.extract_host_port(cfg)
        ping_time = None
        if host and port:
            ping_time = await self.tester.test_connection(host, port)

        return ConfigResult(
            config=cfg,
            protocol=self.categorize_protocol(cfg),
            host=host,
            port=port,
            ping_time=ping_time,
            is_reachable=ping_time is not None
        )

    async def test_configs(
        self, configs: Set[str]
    ) -> List[ConfigResult]:
        """Test a list of configurations for connectivity and latency."""
        semaphore = asyncio.Semaphore(self.settings.network.concurrent_limit)

        async def safe_worker(cfg: str) -> Optional[ConfigResult]:
            async with semaphore:
                try:
                    return await self._test_config(cfg)
                except Exception as exc:
                    logging.debug("test_configs worker failed for %s: %s", cfg, exc)
                    return None

        tasks = [asyncio.create_task(safe_worker(c)) for c in configs]
        try:
            results = await tqdm_asyncio.gather(
                *tasks, total=len(tasks), desc="Testing configs"
            )
            return [res for res in results if res is not None]
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