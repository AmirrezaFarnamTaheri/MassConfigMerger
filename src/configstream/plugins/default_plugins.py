from __future__ import annotations

from pathlib import Path
from typing import Any

import aiohttp

from ..core import Proxy, generate_base64_subscription, generate_clash_config
from . import ExportPlugin, FilterPlugin, SourcePlugin


class UrlSourcePlugin(SourcePlugin):
    """Default plugin for fetching proxies from a URL."""

    @property
    def name(self) -> str:
        return "url_source"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: dict[str, Any]) -> None:
        pass

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def fetch_proxies(self, url: str) -> list[str]:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response.raise_for_status()
                    text = await response.text()
                    return [
                        line.strip() for line in text.splitlines()
                        if line.strip() and not line.strip().startswith("#")
                    ]
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                return []


class CountryFilterPlugin(FilterPlugin):
    """Default plugin for filtering proxies by country."""

    def __init__(self, country: str):
        self._country = country.upper()

    @property
    def name(self) -> str:
        return "country_filter"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: dict[str, Any]) -> None:
        pass

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def filter_proxies(self, proxies: list[Proxy]) -> list[Proxy]:
        return [p for p in proxies if p.country_code.upper() == self._country]


class LatencyFilterPlugin(FilterPlugin):
    """Default plugin for filtering proxies by latency."""

    def __init__(self, max_latency: float):
        self._max_latency = max_latency

    @property
    def name(self) -> str:
        return "latency_filter"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: dict[str, Any]) -> None:
        pass

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def filter_proxies(self, proxies: list[Proxy]) -> list[Proxy]:
        return [
            p for p in proxies if p.latency and p.latency <= self._max_latency
        ]


class Base64ExportPlugin(ExportPlugin):
    """Default plugin for exporting to Base64 subscription."""

    @property
    def name(self) -> str:
        return "base64_export"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: dict[str, Any]) -> None:
        pass

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def export(self, proxies: list[Proxy], output_path: Path) -> None:
        content = generate_base64_subscription(proxies)
        if content:
            (output_path / "vpn_subscription_base64.txt").write_text(
                content, encoding="utf-8")


class ClashExportPlugin(ExportPlugin):
    """Default plugin for exporting to Clash configuration."""

    @property
    def name(self) -> str:
        return "clash_export"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: dict[str, Any]) -> None:
        pass

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def export(self, proxies: list[Proxy], output_path: Path) -> None:
        content = generate_clash_config(proxies)
        if content:
            (output_path / "clash.yaml").write_text(content, encoding="utf-8")
