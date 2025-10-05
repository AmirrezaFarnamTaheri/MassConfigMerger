"""Core component for processing, filtering, and testing VPN configurations.

This module defines the `ConfigProcessor`, a central class responsible for
handling the lifecycle of a configuration: from initial filtering based on
protocol, to testing for connectivity and latency, and finally to normalizing
and categorizing the results. It uses a `NodeTester` for network operations
and produces structured `ConfigResult` objects.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Set

from tqdm.asyncio import tqdm_asyncio

from ..config import Settings
from ..tester import NodeTester
from . import config_normalizer


@dataclass
class ConfigResult:
    """
    Data class for holding the result of processing a single VPN configuration.

    Attributes:
        config: The original configuration string.
        protocol: The detected protocol (e.g., "VMess", "Shadowsocks").
        host: The server hostname or IP address.
        port: The server port.
        ping_time: The latency in seconds, or None if unreachable.
        is_reachable: A boolean indicating if the server is connectable.
        source_url: The URL from which the configuration was fetched.
        country: The ISO 3166-1 alpha-2 country code of the server.
        reliability: A score indicating the historical reliability of the proxy.
    """

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
    """
    A processor for filtering, testing, and normalizing VPN configurations.

    This class encapsulates the logic for handling raw configuration strings,
    applying filters, testing for connectivity, and producing structured
    `ConfigResult` objects.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the ConfigProcessor.

        Args:
            settings: The application settings object.
        """
        self.tester = NodeTester(settings)
        self.settings = settings

    def filter_configs(
        self, configs: Set[str], *, use_fetch_rules: bool = False
    ) -> Set[str]:
        """
        Filter configurations based on protocol rules in the settings.

        This method can operate in two modes:
        1. `use_fetch_rules=True`: Filters based on the `fetch_protocols` list,
           which is a simple inclusion list.
        2. `use_fetch_rules=False`: Filters based on the `merge_include_protocols`
           and `merge_exclude_protocols` sets for more complex filtering.

        Args:
            configs: A set of configuration strings to filter.
            use_fetch_rules: If True, use fetch-stage rules; otherwise, use
                             merge-stage rules.

        Returns:
            A new set containing only the configurations that match the rules.
        """
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
        """Test a single configuration and return a ConfigResult."""
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
        """
        Test a list of configurations for connectivity and latency.

        This method uses a semaphore to limit the number of concurrent tests
        and displays a progress bar.

        Args:
            configs: A set of configuration strings to test.

        Returns:
            A list of `ConfigResult` objects for the tested configurations.
        """
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
        """
        Create a semantic hash for a configuration for intelligent deduplication.

        Args:
            config: The configuration string.

        Returns:
            A hash representing the semantic content of the configuration.
        """
        return config_normalizer.create_semantic_hash(config)

    async def test_connection(self, host: str, port: int) -> Optional[float]:
        """
        Test a connection and measure response time using the NodeTester.

        Args:
            host: The server hostname or IP address.
            port: The server port.

        Returns:
            The latency in seconds, or None if the connection fails.
        """
        return await self.tester.test_connection(host, port)

    async def lookup_country(self, host: str) -> Optional[str]:
        """
        Return the ISO country code for a host using the NodeTester.

        Args:
            host: The server hostname or IP address.

        Returns:
            The ISO 3166-1 alpha-2 country code, or None if not found.
        """
        return await self.tester.lookup_country(host)

    def categorize_protocol(self, config: str) -> str:
        """
        Categorize a configuration by its protocol type.

        Args:
            config: The configuration string.

        Returns:
            A string representing the detected protocol (e.g., "VMess").
        """
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
        """
        Apply mux and smux parameters to URI-style configurations.

        This function modifies the configuration string to include tuning
        parameters as specified in the application settings.

        Args:
            config: The configuration string to tune.

        Returns:
            The modified configuration string.
        """
        return config_normalizer.apply_tuning(config, self.settings)