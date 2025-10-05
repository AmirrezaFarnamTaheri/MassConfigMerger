"""Network testing utilities for VPN nodes.

This module provides the `NodeTester` class, which is a core component for
verifying the connectivity and performance of VPN configurations. It includes
methods for testing TCP connections, measuring latency, resolving hostnames
with an asynchronous DNS resolver, and looking up the geographic location
of servers using a GeoIP database.
"""
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
    """
    A utility class for testing node latency and performing GeoIP lookups.

    This class encapsulates the functionality needed to test network endpoints,
    including asynchronous DNS resolution with caching, TCP connection testing,
    and country lookups based on IP address.
    """

    _geoip_reader: Optional["Reader"]

    def __init__(self, config: Settings) -> None:
        """
        Initialize the NodeTester.

        Args:
            config: The application settings object.
        """
        self.config = config
        self.dns_cache: dict[str, str] = {}
        self.resolver: Optional[AsyncResolver] = None
        self._geoip_reader: Optional["Reader"] = None

    async def _resolve_host(self, host: str) -> str:
        """
        Resolve a hostname to an IP address, with caching.

        This method first checks a local cache for the resolved IP. If not
        found, it attempts to resolve the hostname using an asynchronous DNS
        resolver (`aiodns`) if available, falling back to the standard library's
        blocking `getaddrinfo` executed in a thread pool.

        Args:
            host: The hostname to resolve.

        Returns:
            The resolved IP address as a string, or the original host if
            resolution fails.
        """
        if host in self.dns_cache:
            return self.dns_cache[host]

        if re.match(r"^[0-9.]+$", host):
            return host

        if "aiodns" in sys.modules and AsyncResolver is not None and self.resolver is None:
            try:
                self.resolver = AsyncResolver()
            except Exception as exc:  # pragma: no cover - env specific
                logging.debug("AsyncResolver init failed: %s", exc)

        if self.resolver is not None:
            try:
                result = await self.resolver.resolve(host)
                if result:
                    ip = result[0]["host"]
                    self.dns_cache[host] = ip
                    return ip
            except Exception as exc:  # pragma: no cover - env specific
                logging.debug("Async DNS resolve failed for %s: %s", host, exc)

        try:
            info = await asyncio.get_running_loop().getaddrinfo(host, None)
            ip = info[0][4][0]
            self.dns_cache[host] = ip
            return ip
        except (OSError, socket.gaierror) as exc:
            logging.debug("Standard DNS lookup failed for %s: %s", host, exc)

        return host

    async def test_connection(self, host: str, port: int) -> Optional[float]:
        """
        Test a TCP connection to a given host and port, returning the latency.

        If `enable_url_testing` is disabled in the settings, this method will
        return immediately. Otherwise, it attempts to establish a TCP
        connection and measures the time it takes.

        Args:
            host: The server hostname or IP address.
            port: The server port.

        Returns:
            The connection latency in seconds, or ``None`` if the connection
            fails or is disabled.
        """
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
        """
        Return the ISO country code for a host using the GeoIP database.

        This method resolves the host to an IP address and then performs a
        lookup in the GeoLite2 database specified in the settings. The GeoIP
        database reader is initialized on the first call.

        Args:
            host: The hostname or IP address to look up.

        Returns:
            The ISO 3166-1 alpha-2 country code as a string, or ``None`` if
            the lookup fails or the GeoIP database is not configured.
        """
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
        """
        Gracefully close any open resources, such as the DNS resolver.

        This method should be called after all testing is complete to ensure
        that underlying connections and resources are properly released.
        """
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