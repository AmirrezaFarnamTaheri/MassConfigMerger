import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from .config import AppSettings
from .geoip import GeoIPService
from .parsers import (_parse_generic, _parse_hysteria, _parse_hysteria2,
                    _parse_naive, _parse_ss, _parse_trojan, _parse_tuic,
                    _parse_vless, _parse_vmess, _parse_wireguard)

from .models import Proxy

logger = logging.getLogger(__name__)


class ProxyTestResult:
    def __init__(self,
                 success: bool,
                 latency_ms: Optional[float],
                 geolocation: Optional[dict],
                 timestamp: datetime,
                 proxy: Proxy):
        self.success = success
        self.latency_ms = latency_ms
        self.geolocation = geolocation
        self.timestamp = timestamp
        self.proxy = proxy


class ProxyTester:
    def __init__(self,
                 test_url: str = "http://www.gstatic.com/generate_204",
                 timeout: int = 10,
                 ssl_verify: bool = True,
                 max_workers: int = 10):
        self.test_url = test_url
        self.timeout = timeout
        self.ssl_verify = ssl_verify
        self.geoip_service = GeoIPService()
        self.semaphore = asyncio.Semaphore(max_workers)

    def _build_proxy_url(self, proxy: Proxy) -> str:
        if proxy.uuid:
            return (
                f"{proxy.protocol}://{proxy.uuid}@{proxy.address}:{proxy.port}"
            )
        return f"{proxy.protocol}://{proxy.address}:{proxy.port}"

    async def test(self, proxy: Proxy) -> ProxyTestResult:
        start_time = asyncio.get_event_loop().time()
        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_verify,
                                             ttl_dns_cache=300)
            proxy_url = self._build_proxy_url(proxy)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                        self.test_url,
                        proxy=proxy_url,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        ssl=self.ssl_verify) as response:
                    if response.status == 200:
                        latency = (asyncio.get_event_loop().time() -
                                   start_time) * 1000
                        geolocation = await self.geoip_service.geolocate(proxy)
                        proxy.is_working = True
                        proxy.latency = latency
                        return ProxyTestResult(success=True,
                                               latency_ms=latency,
                                               geolocation=geolocation,
                                               timestamp=datetime.now(),
                                               proxy=proxy)
        except (asyncio.TimeoutError, aiohttp.ClientError, Exception):
            pass
        proxy.is_working = False
        return ProxyTestResult(success=False,
                               latency_ms=None,
                               geolocation=None,
                               timestamp=datetime.now(),
                               proxy=proxy)

    async def test_all(self, proxies: List[Proxy]) -> List[ProxyTestResult]:
        tasks = [self.test(proxy) for proxy in proxies]
        return await asyncio.gather(*tasks)


def parse_config(config_string: str) -> Optional[Proxy]:
    if not config_string or not isinstance(config_string, str):
        return None

    config_string = config_string.strip()
    if not config_string or config_string.startswith("#"):
        return None

    try:
        if config_string.startswith("vmess://"):
            return _parse_vmess(config_string)
        if config_string.startswith("vless://"):
            return _parse_vless(config_string)
        if config_string.startswith("ss://"):
            return _parse_ss(config_string)
        if config_string.startswith("trojan://"):
            return _parse_trojan(config_string)
        if config_string.startswith("hysteria://"):
            return _parse_hysteria(config_string)
        if config_string.startswith("hy2://") or config_string.startswith(
                "hysteria2://"):
            return _parse_hysteria2(config_string)
        if config_string.startswith("tuic://"):
            return _parse_tuic(config_string)
        if config_string.startswith("wg://") or config_string.startswith(
                "wireguard://"):
            return _parse_wireguard(config_string)
        if config_string.startswith("naive+https://"):
            return _parse_naive(config_string)
        if any(
                config_string.startswith(f"{p}://")
                for p in
            ["ssh", "http", "https", "socks", "socks4", "socks5"]):
            return _parse_generic(config_string)

        logger.debug(f"Unknown protocol in config: {config_string[:50]}...")
        return None

    except Exception as e:
        logger.debug(f"Error parsing config: {e}")
        return None


def parse_config_batch(config_strings: list[str]) -> list[Proxy]:
    parsed = []
    for config_string in config_strings:
        proxy = parse_config(config_string)
        if proxy is not None:
            parsed.append(proxy)
    return parsed


async def geolocate_proxy(proxy: Proxy, geoip_reader=None) -> Proxy:
    if geoip_reader is None:
        proxy.country = "Unknown"
        proxy.country_code = "XX"
        return proxy
    try:
        response = geoip_reader.city(proxy.address)
        proxy.country = response.country.name or "Unknown"
        proxy.country_code = response.country.iso_code or "XX"
        proxy.city = response.city.name or "Unknown"
        proxy.asn = f"AS{response.autonomous_system.autonomous_system_number}"
    except Exception:
        proxy.country = "Unknown"
        proxy.country_code = "XX"
    return proxy


async def run_single_proxy_test(config: str,
                                timeout: int = 10) -> ProxyTestResult | None:
    proxy = parse_config(config)
    if proxy:
        tester = ProxyTester(timeout=timeout)
        return await tester.test(proxy)
    return None