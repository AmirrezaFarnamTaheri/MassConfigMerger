from __future__ import annotations

from .core import Proxy
from .services import IProxyRepository


class InMemoryProxyRepository(IProxyRepository):
    """In-memory implementation of the proxy repository."""

    def __init__(self):
        self._proxies: list[Proxy] = []

    async def save(self, proxy: Proxy) -> None:
        self._proxies.append(proxy)

    async def get_all(self) -> list[Proxy]:
        return self._proxies
