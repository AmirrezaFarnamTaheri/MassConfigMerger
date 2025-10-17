from __future__ import annotations

from typing import List

from .core import Proxy
from .services import IProxyRepository


class InMemoryProxyRepository(IProxyRepository):
    """In-memory implementation of the proxy repository."""

    def __init__(self):
        self._proxies: List[Proxy] = []

    async def save(self, proxy: Proxy) -> None:
        self._proxies.append(proxy)

    async def get_all(self) -> List[Proxy]:
        return self._proxies
