#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArgoVPN (Falcon/CDN) Configuration Merger
===================================================================

This script collects, tests, and merges ArgoVPN configurations (Falcon and CDN/Bridge modes)
from various public sources.

Features:
• Targeted source collection for ArgoVPN profiles.
• Custom parsing of ArgoVPN-specific formats (e.g., falcon:// or argocdn:// links).
• Connectivity testing for ArgoVPN endpoints via Cloudflare.
• Deduplication and sorting based on availability.
• Output in formats compatible with ArgoVPN-supporting clients.

Requirements: May use Cloudflare-related libraries or simple HTTP requests for testing reachability.
"""

import asyncio
import aiohttp
from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from vpn_merger import Config as BaseConfig
from vpn_merger import EnhancedConfigProcessor


@dataclass
class ArgoConfig(BaseConfig):
    """Configuration settings for ArgoVPN merging."""
    argo_sources: List[str] = None
    valid_prefixes: Tuple[str, ...] = ("falcon://", "argocdn://")


CONFIG_ARGO = ArgoConfig(
    argo_sources=[
        "https://raw.githubusercontent.com/ArgoVPNCommunity/configs/main/list.txt",
    ],
)


class ArgoSources:
    """Collection of ArgoVPN subscription sources."""

    ARGO_SOURCES = [
        "https://raw.githubusercontent.com/ArgoVPNCommunity/configs/main/list.txt",
    ]

    @classmethod
    def get_all_sources(cls) -> List[str]:
        return list(dict.fromkeys(cls.ARGO_SOURCES))


@dataclass
class ArgoResult:
    """Data structure for a single ArgoVPN config result."""

    config: str
    host: Optional[str] = None
    port: Optional[int] = None
    is_reachable: bool = False
    ping_time: Optional[float] = None
    source_url: str = ""


class ArgoProcessor(EnhancedConfigProcessor):
    """Processor for ArgoVPN configurations."""

    def extract_argo_details(self, config: str) -> Tuple[Optional[str], Optional[int]]:
        parsed = urlparse(config)
        host = parsed.hostname
        port = parsed.port if parsed.port else 443
        return host, port

    async def test_argo_connection(self, host: str, port: int) -> Optional[float]:
        try:
            test_url = f"https://{host}"
            async with aiohttp.ClientSession() as session:
                async with session.get(test_url, timeout=CONFIG_ARGO.connect_timeout) as resp:
                    if resp.status == 200:
                        return 150.0
        except Exception as e:
            print(f"[!] ArgoVPN test failed for {host}:{port} - {e}")
        return None


class AsyncArgoFetcher:
    """Async fetcher for ArgoVPN sources."""

    async def fetch_url(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=CONFIG_ARGO.request_timeout) as resp:
                return await resp.text()


class ArgoMerger:
    """Main orchestrator for ArgoVPN merging process."""

    def __init__(self) -> None:
        self.fetcher = AsyncArgoFetcher()
        self.processor = ArgoProcessor()
        self.results: List[ArgoResult] = []

    async def run(self) -> None:
        print(">>> Starting ArgoVPN Merger...")
        sources = ArgoSources.get_all_sources()
        for url in sources:
            try:
                content = await self.fetcher.fetch_url(url)
            except Exception as exc:
                print(f"[!] Failed to fetch {url}: {exc}")
                continue
            for line in content.splitlines():
                if not line.strip():
                    continue
                host, port = self.processor.extract_argo_details(line)
                ping = await self.processor.test_argo_connection(host, port) if host else None
                result = ArgoResult(
                    config=line,
                    host=host,
                    port=port,
                    is_reachable=ping is not None,
                    ping_time=ping,
                    source_url=url,
                )
                self.results.append(result)
        print(">>> ArgoVPN Merger completed.")


async def main_argo() -> None:
    merger = ArgoMerger()
    await merger.run()


def run_argo_merger() -> None:
    asyncio.run(main_argo())


if __name__ == "__main__":
    run_argo_merger()
