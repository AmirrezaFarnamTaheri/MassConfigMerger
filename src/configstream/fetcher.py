from __future__ import annotations

import logging

import aiohttp

logger = logging.getLogger(__name__)


async def fetch_from_source(
    session: aiohttp.ClientSession, source: str, timeout: int = 30
) -> list[str]:
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
        logger.error("Error fetching source", extra={"source": source, "error": e})
        return []
