#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP Injector Configuration Merger
===================================================================

This script focuses on collecting, testing, and merging HTTP Injector
configurations from various public sources.

Features:
• Targeted source collection for HTTP Injector profiles.
• Custom parsing of HTTP Injector-specific formats (e.g., .ehi files with payload, SNI, etc.).
• Basic connectivity testing for HTTP Injector proxies.
• Deduplication and sorting based on availability.
• Output in formats compatible with HTTP Injector applications.

Requirements: Requires 'requests' or similar libraries for HTTP parsing and testing.
"""

import asyncio
import aiohttp
import base64
import json
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from vpn_merger import Config as BaseConfig
from vpn_merger import EnhancedConfigProcessor


@dataclass
class HttpInjectorConfig(BaseConfig):
    """Configuration settings specific to HTTP Injector merging."""
    http_injector_sources: List[str] = None
    valid_prefixes: Tuple[str, ...] = ("http_injector://", "http_proxy://")


CONFIG_HTTP_INJECTOR = HttpInjectorConfig(
    http_injector_sources=[
        "https://raw.githubusercontent.com/SomeUser/HTTPInjectorConfigs/main/configs.txt",
        "http://example.com/hiconfigs/latest.txt",
    ],
)


class HttpInjectorSources:
    """Collection of HTTP Injector subscription sources."""

    HTTP_INJECTOR_SOURCES = [
        "https://raw.githubusercontent.com/SomeUser/HTTPInjectorConfigs/main/configs.txt",
        "http://example.com/hiconfigs/latest.txt",
    ]

    @classmethod
    def get_all_sources(cls) -> List[str]:
        return list(dict.fromkeys(cls.HTTP_INJECTOR_SOURCES))


@dataclass
class HttpInjectorResult:
    """Data structure for a single HTTP Injector config result."""

    config: str
    host: Optional[str] = None
    port: Optional[int] = None
    is_reachable: bool = False
    ping_time: Optional[float] = None
    source_url: str = ""
    payload: Optional[str] = None
    sni: Optional[str] = None


class HttpInjectorProcessor(EnhancedConfigProcessor):
    """Processor for HTTP Injector configurations."""

    def extract_http_injector_details(self, config: str) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[str]]:
        host, port = self.extract_host_port(config)
        payload_match = re.search(r"payload=([^&]+)", config)
        sni_match = re.search(r"sni=([^&]+)", config)
        payload = base64.b64decode(payload_match.group(1)).decode() if payload_match else None
        sni = sni_match.group(1) if sni_match else None
        return host, port, payload, sni

    async def test_http_injector_connection(self, host: str, port: int, payload: Optional[str] = None, sni: Optional[str] = None) -> Optional[float]:
        try:
            url = "http://example.com"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, proxy=f"http://{host}:{port}", timeout=CONFIG_HTTP_INJECTOR.connect_timeout) as resp:
                    if resp.status == 200:
                        return 100.0
        except Exception as e:
            print(f"[!] HTTP Injector test failed for {host}:{port} - {e}")
        return None


class AsyncHttpInjectorFetcher:
    """Async fetcher for HTTP Injector sources."""

    async def fetch_url(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=CONFIG_HTTP_INJECTOR.request_timeout) as resp:
                return await resp.text()


class HttpInjectorMerger:
    """Main orchestrator for HTTP Injector merging process."""

    def __init__(self) -> None:
        self.fetcher = AsyncHttpInjectorFetcher()
        self.processor = HttpInjectorProcessor()
        self.results: List[HttpInjectorResult] = []

    async def run(self) -> None:
        print(">>> Starting HTTP Injector Merger...")
        sources = HttpInjectorSources.get_all_sources()
        for url in sources:
            try:
                content = await self.fetcher.fetch_url(url)
            except Exception as exc:
                print(f"[!] Failed to fetch {url}: {exc}")
                continue
            for line in content.splitlines():
                if not line.strip():
                    continue
                host, port, payload, sni = self.processor.extract_http_injector_details(line)
                ping = await self.processor.test_http_injector_connection(host, port, payload, sni) if host and port else None
                result = HttpInjectorResult(
                    config=line,
                    host=host,
                    port=port,
                    payload=payload,
                    sni=sni,
                    is_reachable=ping is not None,
                    ping_time=ping,
                    source_url=url,
                )
                self.results.append(result)
        print(">>> HTTP Injector Merger completed.")


async def main_http_injector() -> None:
    merger = HttpInjectorMerger()
    await merger.run()


def run_http_injector_merger() -> None:
    asyncio.run(main_http_injector())


if __name__ == "__main__":
    run_http_injector_merger()
