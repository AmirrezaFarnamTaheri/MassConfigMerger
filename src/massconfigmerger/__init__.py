"""MassConfigMerger package initialization."""

from __future__ import annotations

import aiohttp


if not hasattr(aiohttp.ClientSession, "get_loop"):
    def _get_loop(self: aiohttp.ClientSession):
        return self.loop

    aiohttp.ClientSession.get_loop = _get_loop  # type: ignore[attr-defined]

