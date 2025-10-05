"""A toolchain for collecting, testing, and merging free VPN configurations from public sources."""

from __future__ import annotations

import asyncio
import aiohttp


def get_client_loop(session: aiohttp.ClientSession) -> asyncio.AbstractEventLoop | None:
    """
    Return the event loop used by an aiohttp ClientSession.

    This function provides a compatibility wrapper to get the event loop
    from a session object, accommodating changes in the aiohttp API where
    the `get_loop` method was deprecated and removed. It falls back to
    accessing the internal `_loop` attribute if `get_loop` is not available.

    Args:
        session: The aiohttp client session.

    Returns:
        The asyncio event loop instance, or None if it cannot be determined.
    """
    get_loop = getattr(session, "get_loop", None)
    if callable(get_loop):
        try:
            return get_loop()
        except RuntimeError:
            return None
    return getattr(session, "_loop", None)
