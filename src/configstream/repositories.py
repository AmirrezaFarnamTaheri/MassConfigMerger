from __future__ import annotations

from typing import List
from .core import Proxy
from .services import IProxyRepository
from .database.models import Proxy as ProxyModel

class InMemoryProxyRepository(IProxyRepository):
    """In-memory implementation of the proxy repository."""

    def __init__(self):
        self._proxies: List[ProxyModel] = []

    async def save(self, proxy: Proxy) -> None:
        proxy_model = ProxyModel(
            config=proxy.config,
            protocol=proxy.protocol,
            latency=proxy.latency,
            country=proxy.country,
            country_code=proxy.country_code,
            city=proxy.city,
            asn_name=proxy.asn,
            asn_number=proxy.asn_number,
            remarks=proxy.remarks,
        )
        self._proxies.append(proxy_model)

    async def get_all(self) -> List[Proxy]:
        proxies = []
        for proxy_model in self._proxies:
            proxy = Proxy(
                config=proxy_model.config,
                protocol=proxy_model.protocol,
                latency=proxy_model.latency,
                country=proxy_model.country,
                country_code=proxy_model.country_code,
                city=proxy_model.city,
                asn=proxy_model.asn_name,
                asn_number=proxy_model.asn_number,
                remarks=proxy_model.remarks,
            )
            proxies.append(proxy)
        return proxies