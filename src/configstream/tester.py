from __future__ import annotations

from rich.progress import Progress

from .core import Proxy, test_all_proxies


async def test_configs(configs: list[str], progress: Progress) -> list[Proxy]:
    """
    Tests a list of configurations concurrently and returns their status.
    """
    return await test_all_proxies(configs, progress)