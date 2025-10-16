from __future__ import annotations

import aiohttp


async def fetch_from_source(session: aiohttp.ClientSession, source: str, timeout: int = 30) -> list[str]:
    """Fetch proxy configurations from a source."""
    try:
        async with session.get(source, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            response.raise_for_status()
            text = await response.text()
            return [
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
    except Exception as e:
        print(f"Error fetching {source}: {e}")
        return []