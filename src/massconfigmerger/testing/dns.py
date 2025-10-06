from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import sys
from typing import Optional

try:
    from aiohttp.resolver import AsyncResolver
    import aiodns  # noqa: F401
except Exception:  # pragma: no cover - optional dependency
    AsyncResolver = None  # type: ignore
    aiodns = None  # type: ignore


def is_ip_address(host: str) -> bool:
    """Check if the given host is a valid IP address."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


class DNSResolver:
    """A utility class for asynchronously resolving hostnames."""

    _resolver: Optional[AsyncResolver] = None

    def __init__(self):
        self.dns_cache: dict[str, str] = {}

    def _get_async_resolver(self) -> Optional[AsyncResolver]:
        """Lazily initialize and return the asynchronous DNS resolver."""
        if self._resolver is None and "aiodns" in sys.modules and AsyncResolver:
            try:
                self._resolver = AsyncResolver()
            except Exception as exc:
                logging.debug("AsyncResolver init failed: %s", exc)
        return self._resolver

    async def resolve(self, host: str) -> Optional[str]:
        """Resolve a hostname to an IP address, with caching. Returns None on failure."""
        if host in self.dns_cache:
            return self.dns_cache[host]
        if is_ip_address(host):
            return host

        resolver = self._get_async_resolver()
        if resolver:
            try:
                result = await resolver.resolve(host)
                if result:
                    ip = result[0]["host"]
                    self.dns_cache[host] = ip
                    return ip
            except Exception as exc:
                logging.debug("Async DNS resolve failed for %s: %s", host, exc)

        try:
            info = await asyncio.get_running_loop().getaddrinfo(host, None)
            ip = info[0][4][0]
            self.dns_cache[host] = ip
            return ip
        except (OSError, socket.gaierror) as exc:
            logging.debug("Standard DNS lookup failed for %s: %s", host, exc)
            return None

    async def close(self) -> None:
        """Gracefully close the resolver."""
        if self._resolver:
            try:
                await self._resolver.close()
            except Exception as exc:
                logging.debug("AsyncResolver close failed: %s", exc)
            self._resolver = None