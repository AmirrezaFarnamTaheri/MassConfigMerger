from abc import ABC, abstractmethod
from typing import List

from .core import Proxy


class IProxyRepository(ABC):
    @abstractmethod
    async def save(self, proxy: Proxy) -> None:
        pass

    @abstractmethod
    async def get_all(self) -> List[Proxy]:
        pass


class IProxyTester(ABC):
    @abstractmethod
    async def test(self, proxy: Proxy) -> Proxy:
        pass