from __future__ import annotations

import asyncio
import logging
import re
import socket
import sys
import time
from typing import Optional

try:  # pragma: no cover - optional dependency
    from geoip2.database import Reader
    from geoip2.errors import AddressNotFoundError
except ImportError:
    Reader = None
    AddressNotFoundError = None

try:
    from aiohttp.resolver import AsyncResolver
    import aiodns  # noqa: F401
except Exception:  # pragma: no cover - optional dependency
    AsyncResolver = None  # type: ignore
    aiodns = None  # type: ignore

from .config import Settings


class NodeTester:
    """Utility class for node latency testing and GeoIP lookup."""

    _geoip_reader: Optional["Reader"]

    def __init__(self, config: Settings) -> None:
        self.config = config
        self.dns_cache: dict[str, str] = {}
        self.resolver: Optional[AsyncResolver] = None
        self._geoip_reader: Optional["Reader"] = None

    async def _resolve_host(self, host: str) -> str:
        """Resolve a hostname to an IP address, using a cache."""
        if host in self.dns_cache:
            return self.dns_cache[host]

        # Return early if it's already an IP address
        if re.match(r"^[0-9.]+$", host):
            return host

        # Initialize resolver if needed
        if "aiodns" in sys.modules and AsyncResolver is not None and self.resolver is None:
            try:
                self.resolver = AsyncResolver()
            except Exception as exc:  # pragma: no cover - env specific
                logging.debug("AsyncResolver init failed: %s", exc)

        # Use async resolver if available
        if self.resolver is not None:
            try:
                result = await self.resolver.resolve(host)
                if result:
                    ip = result[0]["host"]
                    self.dns_cache[host] = ip
                    return ip
            except Exception as exc:  # pragma: no cover - env specific
                logging.debug("Async DNS resolve failed for %s: %s", host, exc)

        # Fallback to standard blocking lookup
        try:
            info = await asyncio.get_running_loop().getaddrinfo(host, None)
            ip = info[0][4][0]
            self.dns_cache[host] = ip
            return ip
        except (OSError, socket.gaierror) as exc:
            logging.debug("Standard DNS lookup failed for %s: %s", host, exc)

        return host  # Fallback to the original host if all else fails

    async def test_connection(self, host: str, port: int) -> Optional[float]:
        """Return latency in seconds or ``None`` on failure."""
        if not self.config.processing.enable_url_testing:
            return None

        start_time = time.time()
        try:
            target_ip = await self._resolve_host(host)
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(target_ip, port),
                timeout=self.config.network.connect_timeout,
            )
            writer.close()
            await writer.wait_closed()
            return time.time() - start_time
        except (OSError, asyncio.TimeoutError) as exc:
            logging.debug("Connection test failed for %s:%d: %s", host, port, exc)
            return None

    async def lookup_country(self, host: str) -> Optional[str]:
        """Return ISO country code for ``host`` if GeoIP database configured."""
        if not host or not self.config.processing.geoip_db or not Reader:
            return None

        if self._geoip_reader is None:
            try:
                self._geoip_reader = Reader(self.config.processing.geoip_db)
            except OSError as exc:
                logging.debug("GeoIP reader init failed: %s", exc)
                self._geoip_reader = None
                return None

        try:
            ip = await self._resolve_host(host)
            assert self._geoip_reader is not None
            resp = self._geoip_reader.country(ip)
            return resp.country.iso_code
        except (OSError, socket.gaierror, AddressNotFoundError) as exc:
            logging.debug("GeoIP lookup failed for %s: %s", host, exc)
            return None

    async def close(self) -> None:
        """Close any resolver resources if initialized."""
        if self.resolver is not None:
            try:
                close = getattr(self.resolver, "close", None)
                if asyncio.iscoroutinefunction(close):
                    await close()  # type: ignore[misc]
                elif callable(close):
                    close()
            except Exception as exc:  # pragma: no cover - env specific
                logging.debug("Resolver close failed: %s", exc)
            self.resolver = None

        if self._geoip_reader is not None:
            reader = self._geoip_reader
            self._geoip_reader = None
            try:
                close = getattr(reader, "close", None)
                if asyncio.iscoroutinefunction(close):
                    await close()  # type: ignore[misc]
                elif callable(close):
                    close()
            except Exception as exc:  # pragma: no cover - env specific
                logging.debug("GeoIP reader close failed: %s", exc)