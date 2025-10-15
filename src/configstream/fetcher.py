from __future__ import annotations

import asyncio

import aiohttp
from rich.progress import Progress

from .core import fetch_from_source


async def fetch_all(sources: list[str], progress: Progress) -> list[str]:
    """
    Fetches all configurations from the given sources concurrently.
    """
    task = progress.add_task("[green]Fetching sources...", total=len(sources))
    all_configs: list[str] = []

    async with aiohttp.ClientSession() as session:

        async def _fetch_and_update(source: str):
            configs = await fetch_from_source(session, source)
            all_configs.extend(configs)
            progress.update(task, advance=1)

        await asyncio.gather(*[_fetch_and_update(s) for s in sources])

    # Remove duplicate configurations
    return list(dict.fromkeys(all_configs))