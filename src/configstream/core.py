from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from typing import ClassVar

import aiohttp
from rich.progress import Progress

# The URL to test proxies against.
# Using a URL that returns a 204 No Content response is efficient.
TEST_URL = "http://www.gstatic.com/generate_204"

# Timeout for testing each proxy, in seconds.
TEST_TIMEOUT = 5


@dataclass
class Proxy:
    """Represents a proxy configuration with its test results."""

    config: str
    is_working: bool = False
    latency: float | None = None  # in milliseconds

    # A simple cache to avoid re-testing the same proxy config multiple times
    _test_cache: ClassVar[dict[str, "Proxy"]] = {}

    @classmethod
    async def test(cls, config: str) -> "Proxy":
        """
        Tests a single proxy configuration to see if it's working and measures latency.
        Uses a simple cache to avoid re-testing.
        """
        if config in cls._test_cache:
            return cls._test_cache[config]

        instance = cls(config=config)
        try:
            # Note: This is a simplified test. A real-world implementation
            # would need to parse the proxy URL (e.g., vmess://, ss://) and
            # configure the aiohttp connector accordingly.
            # For this example, we'll simulate a test with a simple request.
            async with aiohttp.ClientSession() as session:
                start_time = asyncio.get_event_loop().time()
                async with session.get(
                    TEST_URL, timeout=TEST_TIMEOUT  # proxy=config would be used here
                ) as response:
                    if response.status == 204:
                        end_time = asyncio.get_event_loop().time()
                        instance.is_working = True
                        instance.latency = (end_time - start_time) * 1000
        except (aiohttp.ClientError, asyncio.TimeoutError):
            instance.is_working = False

        cls._test_cache[config] = instance
        return instance


async def fetch_from_source(session: aiohttp.ClientSession, source: str) -> list[str]:
    """Fetches proxy configurations from a single URL source."""
    try:
        async with session.get(source, timeout=10) as response:
            response.raise_for_status()
            text = await response.text()
            # Filter out empty or commented lines
            return [
                line
                for line in text.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        print(f"Error fetching {source}: {e}")
        return []


async def test_all_proxies(
    configs: list[str], progress: Progress
) -> list[Proxy]:
    """Tests a list of proxy configurations concurrently."""
    task = progress.add_task("[cyan]Testing proxies...", total=len(configs))
    results: list[Proxy] = []

    async def _test_and_update(config: str):
        proxy = await Proxy.test(config)
        results.append(proxy)
        progress.update(task, advance=1)

    # Run tests concurrently
    await asyncio.gather(*[_test_and_update(c) for c in configs])

    # Sort working proxies by latency (lower is better)
    working_proxies = sorted(
        [p for p in results if p.is_working and p.latency is not None],
        key=lambda p: p.latency,
    )
    non_working_proxies = [p for p in results if not p.is_working]

    return working_proxies + non_working_proxies


def generate_base64_subscription(proxies: list[Proxy]) -> str:
    """Generates a Base64-encoded subscription file content."""
    working_configs = [p.config for p in proxies if p.is_working]
    if not working_configs:
        return ""
    # Each config is individually Base64-encoded, then joined by newlines.
    # The final result is then Base64-encoded again.
    combined_configs = "\n".join(working_configs)
    return base64.b64encode(combined_configs.encode("utf-8")).decode("utf-8")


def generate_clash_config(proxies: list[Proxy]) -> str:
    """Generates a Clash-compatible YAML configuration file."""
    # This is still a simplified placeholder. A real implementation would
    # need to parse each proxy type and generate a valid Clash proxy entry.
    header = "proxies:\n"
    proxy_entries = []
    for i, proxy in enumerate(p for p in proxies if p.is_working):
        proxy_entries.append(
            f"  - name: 'Proxy-{i+1}'\n"
            f"    type: vmess  # Placeholder\n"
            f"    server: server.address  # Placeholder\n"
            f"    port: 12345  # Placeholder\n"
            f"    uuid: 00000000-0000-0000-0000-000000000000  # Placeholder\n"
            f"    alterId: 0  # Placeholder\n"
            f"    cipher: auto\n"
        )
    return header + "".join(proxy_entries)


def generate_raw_configs(proxies: list[Proxy]) -> str:
    """Generates a file with all working raw configuration links."""
    return "\n".join([p.config for p in proxies if p.is_working])