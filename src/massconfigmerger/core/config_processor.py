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
from functools import lru_cache
from typing import List, Optional, Set

from tqdm.asyncio import tqdm_asyncio

from ..config import Settings
from ..tester import BlocklistChecker, NodeTester
from . import config_normalizer


@lru_cache(maxsize=None)
def categorize_protocol(config: str) -> str:
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
    isp: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
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
        self.blocklist_checker = BlocklistChecker(settings)
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
                cfg for cfg in configs if categorize_protocol(cfg).upper() in include_protos
            }
        else:
            # Use merge_include/exclude_protocols for more complex filtering.
            include_protos = self.settings.filtering.merge_include_protocols
            exclude_protos = self.settings.filtering.merge_exclude_protocols
            if not include_protos and not exclude_protos:
                return configs

            filtered = set()
            for cfg in configs:
                proto = categorize_protocol(cfg).upper()
                if include_protos and proto not in include_protos:
                    continue
                if exclude_protos and proto in exclude_protos:
                    continue
                filtered.add(cfg)
            return filtered

    def _filter_by_isp(self, results: List[ConfigResult]) -> List[ConfigResult]:
        """Filter results based on ISP include/exclude lists."""
        include = self.settings.filtering.include_isps
        exclude = self.settings.filtering.exclude_isps

        if not include and not exclude:
            return results

        # Normalize filter lists to lowercase for case-insensitive matching
        include_lower = {i.lower() for i in include} if include else set()
        exclude_lower = {e.lower() for e in exclude} if exclude else set()

        def is_match(result: ConfigResult) -> bool:
            if not result.isp:
                # Keep configs without ISP info if we are only excluding
                return not include

            isp_lower = result.isp.lower()

            if include_lower and not any(i in isp_lower for i in include_lower):
                return False

            if exclude_lower and any(e in isp_lower for e in exclude_lower):
                return False

            return True

        return [res for res in results if is_match(res)]

    async def _test_config(self, cfg: str, history: dict) -> ConfigResult:
        """Test a single configuration and return a ConfigResult."""
        host, port = config_normalizer.extract_host_port(cfg)
        ping_time = None
        if host and port:
            ping_time, geo_data = await asyncio.gather(
                self.tester.test_connection(host, port),
                self.tester.lookup_geo_data(host),
            )
        else:
            ping_time, geo_data = None, (None, None, None, None)

        country, isp, latitude, longitude = geo_data
        key = f"{host}:{port}"
        stats = history.get(key)
        reliability = None
        if stats and (stats["successes"] + stats["failures"]) > 0:
            reliability = stats["successes"] / (stats["successes"] + stats["failures"])

        return ConfigResult(
            config=cfg,
            protocol=categorize_protocol(cfg),
            host=host,
            port=port,
            ping_time=ping_time,
            is_reachable=ping_time is not None,
            country=country,
            isp=isp,
            latitude=latitude,
            longitude=longitude,
            reliability=reliability,
        )

    async def _filter_malicious(
        self, results: List[ConfigResult]
    ) -> List[ConfigResult]:
        """Filter out results with malicious IPs concurrently."""
        if (
            not self.settings.security.apivoid_api_key
            or self.settings.security.blocklist_detection_threshold <= 0
        ):
            return results

        async def _check(result: ConfigResult) -> Optional[ConfigResult]:
            """Check a single result for malicious IP, with error handling."""
            if not result.is_reachable or not result.host:
                return result

            ip = None
            try:
                ip = await self.tester.resolve_host(result.host)
            except Exception as exc:
                logging.debug("Failed to resolve host %s: %s", result.host, exc)
                return result  # Keep config if DNS fails

            if not ip:
                return result  # Keep config if host cannot be resolved

            try:
                if await self.blocklist_checker.is_malicious(ip):
                    return None  # Discard if malicious
                return result  # Keep if not malicious
            except Exception as exc:
                logging.debug("Blocklist check failed for %s: %s", ip, exc)
                return result  # Keep config if blocklist check fails

        tasks = [_check(r) for r in results]
        checked_results = await asyncio.gather(*tasks)
        return [res for res in checked_results if res is not None]

    async def test_configs(
        self, configs: Set[str], history: dict | None = None
    ) -> List[ConfigResult]:
        """
        Test a list of configurations for connectivity and latency.

        This method uses a semaphore to limit the number of concurrent tests
        and displays a progress bar.

        Args:
            configs: A set of configuration strings to test.
            history: The proxy history from the database.

        Returns:
            A list of `ConfigResult` objects for the tested configurations.
        """
        if history is None:
            history = {}
        semaphore = asyncio.Semaphore(self.settings.network.concurrent_limit)

        async def safe_worker(cfg: str) -> Optional[ConfigResult]:
            async with semaphore:
                try:
                    return await self._test_config(cfg, history)
                except Exception as exc:
                    logging.debug("test_configs worker failed for %s: %s", cfg, exc)
                    return None

        tasks = [asyncio.create_task(safe_worker(c)) for c in configs]
        try:
            results = await tqdm_asyncio.gather(
                *tasks, total=len(tasks), desc="Testing configs"
            )
            results = [res for res in results if res is not None]
            results = self._filter_by_isp(results)
            return await self._filter_malicious(results)
        except Exception as exc:
            logging.debug("An error occurred during config testing: %s", exc)
            return []
        finally:
            if self.tester:
                await self.tester.close()
            if self.blocklist_checker:
                await self.blocklist_checker.close()

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

    async def lookup_geo_data(self, host: str) -> tuple:
        """
        Return the geo-data for a host using the NodeTester.

        Args:
            host: The server hostname or IP address.

        Returns:
            A tuple containing country, ISP, latitude, and longitude.
        """
        return await self.tester.lookup_geo_data(host)

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