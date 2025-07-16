"""MassConfigMerger package initialization."""

from __future__ import annotations

import asyncio
import aiohttp


def get_client_loop(session: aiohttp.ClientSession) -> asyncio.AbstractEventLoop | None:
    """Return the event loop used by ``session`` if it can be determined."""
    get_loop = getattr(session, "get_loop", None)
    if callable(get_loop):
        try:
            return get_loop()
        except RuntimeError:
            return None
    return getattr(session, "_loop", None)
