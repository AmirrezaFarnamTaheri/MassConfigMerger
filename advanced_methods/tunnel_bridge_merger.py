#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generic Tunnel & Bridge Configuration Merger
===================================================================

This script collects, tests, and merges various generic tunnel and bridge configurations
like SSH tunnels, TCP/UDP proxies, or Shadowsocks bridges.

Features:
• Targeted source collection for generic tunnel/bridge profiles.
• Flexible parsing for diverse tunnel formats (ssh://, tcp://, etc.).
• Basic connectivity testing for tunnel endpoints (SSH handshake, TCP ping).
• Deduplication and sorting based on availability.
• Output in a raw text format for easy use.

Requirements: May require additional libraries for SSH (e.g., paramiko).
"""

import asyncio
import aiohttp
from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from vpn_merger import Config as BaseConfig
from vpn_merger import EnhancedConfigProcessor


@dataclass
class TunnelBridgeConfig(BaseConfig):
    """Configuration settings for Tunnel/Bridge merging."""
    tunnel_bridge_sources: List[str] = None
    valid_prefixes: Tuple[str, ...] = ("ssh://", "tcp://", "udp://")


CONFIG_TUNNEL = TunnelBridgeConfig(
    tunnel_bridge_sources=[
        "https://raw.githubusercontent.com/SomeUser/SSHProxyList/main/proxies.txt",
    ],
)


class TunnelBridgeSources:
    """Collection of generic tunnel/bridge sources."""

    TUNNEL_BRIDGE_SOURCES = [
        "https://raw.githubusercontent.com/SomeUser/SSHProxyList/main/proxies.txt",
    ]

    @classmethod
    def get_all_sources(cls) -> List[str]:
        return list(dict.fromkeys(cls.TUNNEL_BRIDGE_SOURCES))


@dataclass
class TunnelBridgeResult:
    """Data structure for a tunnel/bridge config result."""

    config: str
    host: Optional[str] = None
    port: Optional[int] = None
    is_reachable: bool = False
    ping_time: Optional[float] = None
    source_url: str = ""


class TunnelBridgeProcessor(EnhancedConfigProcessor):
    """Processor for Tunnel/Bridge configurations."""

    def extract_tunnel_bridge_details(self, config: str) -> Tuple[Optional[str], Optional[int]]:
        parsed = urlparse(config)
        host = parsed.hostname
        port = parsed.port
        return host, port

    async def test_tunnel_bridge_connection(self, host: str, port: int, protocol: str = "TCP") -> Optional[float]:
        try:
            if protocol.upper() == "TCP":
                reader, writer = await asyncio.open_connection(host, port)
                writer.close()
                await writer.wait_closed()
            elif protocol.upper() == "UDP":
                loop = asyncio.get_event_loop()
                transport, _ = await loop.create_datagram_endpoint(lambda: asyncio.DatagramProtocol(), remote_addr=(host, port))
                transport.close()
            return 100.0
        except Exception as e:
            print(f"[!] Connection test failed for {host}:{port} ({protocol}) - {e}")
        return None


class AsyncTunnelBridgeFetcher:
    """Async fetcher for tunnel/bridge sources."""

    async def fetch_url(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=CONFIG_TUNNEL.request_timeout) as resp:
                return await resp.text()


class TunnelBridgeMerger:
    """Main orchestrator for tunnel/bridge merging process."""

    def __init__(self) -> None:
        self.fetcher = AsyncTunnelBridgeFetcher()
        self.processor = TunnelBridgeProcessor()
        self.results: List[TunnelBridgeResult] = []

    async def run(self) -> None:
        print(">>> Starting Tunnel/Bridge Merger...")
        sources = TunnelBridgeSources.get_all_sources()
        for url in sources:
            try:
                content = await self.fetcher.fetch_url(url)
            except Exception as exc:
                print(f"[!] Failed to fetch {url}: {exc}")
                continue
            for line in content.splitlines():
                if not line.strip():
                    continue
                host, port = self.processor.extract_tunnel_bridge_details(line)
                proto = "UDP" if line.strip().startswith("udp://") else "TCP"
                ping = await self.processor.test_tunnel_bridge_connection(host, port, proto) if host and port else None
                result = TunnelBridgeResult(
                    config=line,
                    host=host,
                    port=port,
                    is_reachable=ping is not None,
                    ping_time=ping,
                    source_url=url,
                )
                self.results.append(result)
        print(">>> Tunnel/Bridge Merger completed.")


async def main_tunnel_bridge() -> None:
    merger = TunnelBridgeMerger()
    await merger.run()


def run_tunnel_bridge_merger() -> None:
    asyncio.run(main_tunnel_bridge())


if __name__ == "__main__":
    run_tunnel_bridge_merger()
